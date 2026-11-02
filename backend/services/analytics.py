"""Read-only, bounded SQL/MongoDB vehicle analytics with explicit counting units."""

from calendar import monthrange
from datetime import date, datetime, time, timezone


INTERPRETATION = (
    'Complaint counts are reports, not confirmed defects, unique incidents or safety ratings. '
    'The received-date window filters complaints only; recall and investigation counts use all stored dates. '
    'Components overlap. Official totals count distinct records across selected model years. '
    'No vehicle-population or mileage denominator is available for a defect-rate comparison.'
)


def months_between(start, end):
    return (end.year-start.year)*12 + end.month-start.month + 1


def model_rows(connection, make, model, year):
    where, values = 'make=%s AND model=%s', [make, model]
    if year is not None:
        where += ' AND year=%s'; values.append(year)
    rows = connection.execute('''SELECT model_year_id,make,model,year,recall_count,investigation_count
        FROM vehicle_safety_summary WHERE ''' + where + ' ORDER BY year,model_year_id', values).fetchall()
    if not rows:
        return None
    totals = connection.execute('''WITH selected AS (
        SELECT model_year_id FROM vehicle_catalogue WHERE ''' + where + ''')
        SELECT (SELECT count(DISTINCT r.recall_id) FROM research_recall_vehicle r JOIN selected s USING(model_year_id)),
               (SELECT count(DISTINCT i.investigation_id) FROM research_investigation_vehicle i JOIN selected s USING(model_year_id))''', values).fetchone()
    return rows, totals


def complaint_pipeline(identifiers, start, end):
    window = {'$match': {'receivedDate': {
        '$gte': datetime.combine(start,time.min,timezone.utc),
        '$lte': datetime.combine(end,time(23,59,59,999000),timezone.utc)}}}
    components = {'$setDifference': [{'$ifNull': ['$components',[]]},['']]}
    totals = {'_id': None, 'count': {'$sum': 1},
              'withoutComponents': {'$sum': {'$cond': [{'$eq': [{'$size': components},0]},1,0]}}}
    for name in ['crash','fire','injuries','fatalities']:
        for suffix, operator, value in [('Positive','$eq' if name in ['crash','fire'] else '$gt',True if name in ['crash','fire'] else 0),
                                         ('Negative','$eq',False if name in ['crash','fire'] else 0)]:
            totals[name+suffix]={'$sum': {'$cond': [{operator: ['$incident.'+name,value]},1,0]}}
    return [
        {'$match': {'modelYearId': {'$in': identifiers}}},
        {'$project': {'_id':0,'modelYearId':1,'receivedDate':1,'components':1,'incident':1}},
        {'$facet': {
            'summary': [window,{'$group':totals}],
            'components': [window,{'$project':{'components':components}},{'$unwind':'$components'},
                           {'$group':{'_id':'$components','count':{'$sum':1}}},
                           {'$sort':{'count':-1,'_id':1}},{'$limit':11}],
            'months': [window,{'$group':{'_id':{'$dateToString':{'format':'%Y-%m','date':'$receivedDate','timezone':'UTC'}},'count':{'$sum':1}}},{'$sort':{'_id':1}}],
            'byVehicle': [window,{'$group':{'_id':'$modelYearId','count':{'$sum':1}}}],
            'coverage': [{'$group':{'_id':None,'count':{'$sum':1},
                'undated':{'$sum':{'$cond':[{'$eq':[{'$type':'$receivedDate'},'date']},0,1]}},
                'firstReceived':{'$min':'$receivedDate'},'lastReceived':{'$max':'$receivedDate'}}}],
        }},
    ]


def vehicle_analytics(connection, database, *, make, model, year=None, received_from, received_to):
    resolved = model_rows(connection,make,model,year)
    if resolved is None:
        return None
    rows, official = resolved
    identifiers = [row[0] for row in rows]
    with database.complaints.aggregate(complaint_pipeline(identifiers,received_from,received_to),maxTimeMS=5000) as cursor:
        aggregate = next(cursor, {})
    summary = next(iter(aggregate.get('summary',[])),{})
    total = summary.get('count',0)
    incident = {}
    for name in ['crash','fire','injuries','fatalities']:
        positive, negative = summary.get(name+'Positive',0), summary.get(name+'Negative',0)
        incident[name] = {'positive':positive,'negative':negative,'unknown':total-positive-negative}
    coverage = next(iter(aggregate.get('coverage',[])),{})
    by_month = {row['_id']:row['count'] for row in aggregate.get('months',[])}
    monthly = []
    for offset in range(months_between(received_from,received_to)):
        ordinal = received_from.year*12+received_from.month-1+offset
        first = date(ordinal//12,ordinal%12+1,1)
        last = date(first.year,first.month,monthrange(first.year,first.month)[1])
        key = first.strftime('%Y-%m')
        monthly.append({'month':key,'count':by_month.get(key,0),
                        'receivedFrom':max(first,received_from).isoformat(),'receivedTo':min(last,received_to).isoformat(),
                        'partialMonth':first<received_from or last>received_to})
    by_vehicle = {row['_id']:row['count'] for row in aggregate.get('byVehicle',[])}
    return {
        'selection':{'make':make,'model':model,'year':year,'receivedFrom':received_from.isoformat(),'receivedTo':received_to.isoformat()},
        'summary':{'vehicleIdentities':len(rows),'consumerComplaints':total,'officialRecallCampaigns':official[0],
                   'officialInvestigations':official[1],'complaintsWithoutComponents':summary.get('withoutComponents',0)},
        'components':[{'component':row['_id'],'count':row['count']} for row in aggregate.get('components',[])[:10]],
        'componentsTruncated':len(aggregate.get('components',[]))>10,
        'monthly':monthly,'incidentReports':incident,
        'modelYears':[{'modelYearId':identifier,'make':v_make,'model':v_model,'year':v_year,
                       'consumerComplaints':by_vehicle.get(identifier,0),'officialRecallCampaigns':recalls,'officialInvestigations':investigations}
                      for identifier,v_make,v_model,v_year,recalls,investigations in rows],
        'coverage':{'documentsInVehicleScope':coverage.get('count',0),'undatedComplaintsInVehicleScope':coverage.get('undated',0),
                    **{key:coverage[key].date().isoformat() if coverage.get(key) else None for key in ['firstReceived','lastReceived']}},
        'generatedAtUtc':datetime.now(timezone.utc).isoformat(),'interpretation':INTERPRETATION,
    }
