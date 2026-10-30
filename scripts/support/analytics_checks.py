"""Native read checks plus an owned, validator-backed temporary complaint collection."""

from collections import Counter
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from backend.services.analytics import vehicle_analytics
from backend.services.complaints import complaint_query
from mongodb.schema import SCHEMAS
from project_config import app_postgres, mongo_client, mongo_database


def native_analytics_checks():
    assertions=[]
    with app_postgres() as connection,mongo_client() as client:
        database=mongo_database(client)
        options={'make':'HONDA','model':'CIVIC','year':2022,'received_from':date(2020,1,1),'received_to':date(2026,10,22)}
        real=vehicle_analytics(connection,database,**options)
        assert real['summary']['consumerComplaints']==885 and real['summary']['officialRecallCampaigns']==4 and real['summary']['officialInvestigations']==2
        query=complaint_query(model_year_id=17527,received_from=options['received_from'],received_to=options['received_to'])
        dates=Counter()
        for document in database.complaints.find(query,{'receivedDate':1},max_time_ms=5000):
            dates[document['receivedDate'].strftime('%Y-%m')]+=1
        assert dates==Counter({row['month']:row['count']for row in real['monthly']if row['count']})
        assert real['components'][0]=={'component':'STEERING','count':732}
        assert database.complaints.count_documents({**query,'components':'STEERING'},maxTimeMS=5000)==732
        assertions.append('Real Civic 2022 totals are 885 received complaints / 4 campaigns / 2 investigations; monthly values match an independent date count and STEERING matches 732 documents.')
        comparison=vehicle_analytics(connection,database,**{**options,'year':None})
        independent=connection.execute('''SELECT count(DISTINCT r.recall_id) FROM research_recall_vehicle r
            JOIN vehicle_catalogue v USING(model_year_id) WHERE v.make=%s AND v.model=%s''',('HONDA','CIVIC')).fetchone()[0]
        assert comparison['summary']['officialRecallCampaigns']==independent
        assert sum(row['officialRecallCampaigns']for row in comparison['modelYears'])>independent
        assert sum(row['consumerComplaints']for row in comparison['modelYears'])==comparison['summary']['consumerComplaints']
        assertions.append('All-Civic comparison counts distinct official campaigns across years, while complaint counts partition by canonical vehicle identity.')
        name='analytics_verification_'+uuid4().hex
        database.create_collection(name,validator={'$jsonSchema':SCHEMAS['complaints']})
        collection=database[name]
        try:
            times=[datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,1,31,23,59,59,999000,tzinfo=timezone.utc),datetime(2026,3,1,tzinfo=timezone.utc),datetime(2026,3,31,23,59,59,999000,tzinfo=timezone.utc),datetime(2026,4,1,tzinfo=timezone.utc),None]
            components=[['STEERING','BRAKES'],['STEERING'],[],['BRAKES','STEERING'],['OTHER'],['STEERING']]
            incidents=[{'crash':True,'fire':False,'injuries':1,'fatalities':0},{'crash':False,'fire':True,'injuries':0,'fatalities':1},{},{'crash':None,'fire':False,'injuries':None,'fatalities':0},{},{}]
            documents=[]
            for index,received in enumerate(times):
                documents.append({'_id':f'{name}-{index}','odiNumber':str(99000+index),'modelYearId':17527,'vehicle':{'make':'HONDA','model':'CIVIC','year':2022},'components':components[index],'incident':incidents[index],'narrative':'Synthetic analytics fixture','receivedDate':received,'source':{'archives':['synthetic'],'rowIds':[str(index)]}})
            collection.insert_many(documents)
            fixture=SimpleNamespace(complaints=collection)
            result=vehicle_analytics(connection,fixture,**{**options,'received_from':date(2026,1,1),'received_to':date(2026,3,31)})
            assert result['summary']['consumerComplaints']==4
            assert [row['count']for row in result['monthly']]==[2,0,2]
            assert result['components']==[{'component':'STEERING','count':3},{'component':'BRAKES','count':2}]
            assert result['summary']['complaintsWithoutComponents']==1
            assert result['coverage']['documentsInVehicleScope']==6 and result['coverage']['undatedComplaintsInVehicleScope']==1
            assert result['coverage']['firstReceived']=='2026-01-01' and result['coverage']['lastReceived']=='2026-04-01'
            assert result['incidentReports']['crash']=={'positive':1,'negative':1,'unknown':2}
            assert result['incidentReports']['injuries']=={'positive':1,'negative':1,'unknown':2}
            assert result['incidentReports']['fatalities']=={'positive':1,'negative':2,'unknown':1}
            assertions.append('Native aggregation includes UTC day boundaries, zero-fills February, keeps unknown flags/counts separate, counts overlapping component mentions, and excludes undated documents from the dated window.')
            partial=vehicle_analytics(connection,fixture,**{**options,'received_from':date(2026,1,15),'received_to':date(2026,3,15)})
            assert partial['summary']['consumerComplaints']==2
            assert [row['partialMonth']for row in partial['monthly']]==[True,False,True]
            assert partial['summary']['officialRecallCampaigns']==4
            assertions.append('A partial received-date window clips complaint counts/month links while official totals retain all stored dates.')
            collection.delete_many({})
            empty=vehicle_analytics(connection,fixture,**options)
            assert empty['summary']['consumerComplaints']==0 and all(row['count']==0 for row in empty['monthly'])
            assertions.append('An empty complaint collection still returns a valid catalogue scope with zero-valued charts and official counts.')
        finally:
            if not name.startswith('analytics_verification_') or name in {'complaints','case_details'}:
                raise RuntimeError('Unexpected analytics fixture cleanup target')
            database.drop_collection(name)
        assert name not in database.list_collection_names()
    return {'assertions':assertions,'owned_collection_removed':True,'civic_2022':real['summary'],'all_civic_distinct_campaigns':independent}
