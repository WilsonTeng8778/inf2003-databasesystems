"""Read-only analytics contracts, counting edge cases and bounded queries without native DBs."""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock

from psycopg import OperationalError
from pymongo.errors import ExecutionTimeout

from backend import create_app
from backend.services.analytics import complaint_pipeline, vehicle_analytics


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.sql=Mock();self.connect=Mock(return_value=self.sql)
        self.database=Mock();self.mongo=Mock();self.mongo.__getitem__=Mock(return_value=self.database)
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test-only','DUMMY_PASSWORD_HASH':'unused','PG_CONNECT':self.connect,'MONGO_CLIENT_FACTORY':lambda:self.mongo})
        self.client=self.app.test_client()
        self.query='/api/analytics/vehicle?make=honda&model=civic&year=2022&receivedFrom=2026-01-15&receivedTo=2026-03-15'
        self.sql.execute.side_effect=[Mock(fetchall=lambda:[(17527,'HONDA','CIVIC',2022,4,2)]),Mock(fetchone=lambda:(4,2))]
        self.aggregate={'summary':[{'count':4,'withoutComponents':1,'crashPositive':1,'crashNegative':1}],
                        'components':[{'_id':'STEERING','count':3},{'_id':'BRAKES','count':2}],
                        'months':[{'_id':'2026-01','count':2},{'_id':'2026-03','count':2}],
                        'byVehicle':[{'_id':17527,'count':4}],
                        'coverage':[{'count':6,'undated':1,'firstReceived':datetime(2026,1,1,tzinfo=timezone.utc),'lastReceived':datetime(2026,4,1,tzinfo=timezone.utc)}]}
        cursor=Mock();cursor.__enter__=Mock(return_value=iter([self.aggregate]));cursor.__exit__=Mock(return_value=False)
        self.database.complaints.aggregate.return_value=cursor

    def test_public_analytics_normalizes_and_combines_distinct_counting_units(self):
        result=self.client.get(self.query)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['selection']['make'],'HONDA')
        self.assertEqual(result.json['summary']['officialRecallCampaigns'],4)
        self.assertEqual(result.json['summary']['consumerComplaints'],4)
        self.assertEqual(result.json['modelYears'][0]['consumerComplaints'],4)
        self.assertEqual(result.json['coverage']['undatedComplaintsInVehicleScope'],1)
        self.assertEqual(self.sql.execute.call_args.args[1],['HONDA','CIVIC',2022])
        self.assertIn('DISTINCT r.recall_id',self.sql.execute.call_args.args[0]);self.sql.close.assert_called_once()

    def test_months_are_zero_filled_and_partial_boundaries_explicit(self):
        result=self.client.get(self.query).json
        self.assertEqual([row['count']for row in result['monthly']],[2,0,2])
        self.assertEqual([row['partialMonth']for row in result['monthly']],[True,False,True])
        self.assertEqual(result['monthly'][0]['receivedFrom'],'2026-01-15')
        self.assertEqual(result['monthly'][-1]['receivedTo'],'2026-03-15')

    def test_incident_unknowns_and_overlapping_component_mentions_remain_separate(self):
        result=self.client.get(self.query).json
        self.assertEqual(result['incidentReports']['crash'],{'positive':1,'negative':1,'unknown':2})
        self.assertGreater(sum(row['count']for row in result['components']),result['summary']['consumerComplaints'])
        self.assertFalse(result['componentsTruncated'])

    def test_component_output_is_limited_and_marks_more_categories(self):
        self.aggregate['components']=[{'_id':str(n),'count':20-n}for n in range(11)]
        result=self.client.get(self.query).json
        self.assertEqual(len(result['components']),10);self.assertTrue(result['componentsTruncated'])

    def test_empty_mongo_scope_returns_zeroes_with_valid_sql_identity(self):
        self.aggregate.clear()
        result=self.client.get(self.query)
        self.assertEqual(result.status_code,200);self.assertEqual(result.json['summary']['consumerComplaints'],0)
        self.assertEqual([row['count']for row in result.json['monthly']],[0,0,0])
        self.assertIsNone(result.json['coverage']['lastReceived'])

    def test_missing_catalogue_scope_does_not_query_mongodb(self):
        self.sql.execute.side_effect=None;self.sql.execute.return_value.fetchall.return_value=[]
        self.assertEqual(self.client.get(self.query).status_code,404);self.database.complaints.aggregate.assert_not_called()

    def test_invalid_queries_are_rejected_before_connecting(self):
        base='/api/analytics/vehicle?make=HONDA&model=CIVIC'
        paths=[base,base+'&receivedFrom=2026-03-02&receivedTo=2026-01-01',base+'&receivedFrom=bad&receivedTo=2026-01-01',
               base+'&receivedFrom=1900-01-01&receivedTo=2026-01-01',self.query+'&year=2022',self.query+'&x=1',
               self.query.replace('year=2022','year=2101'),self.query.replace('make=honda','make='),
               self.query.replace('receivedFrom=2026-01-15','receivedFrom=1800-01-01')]
        for path in paths:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,400)
        self.connect.assert_not_called()

    def test_aggregate_has_bounded_facets_utc_window_and_no_private_projections(self):
        self.client.get(self.query)
        pipeline=self.database.complaints.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0],{'$match':{'modelYearId':{'$in':[17527]}}})
        self.assertEqual(self.database.complaints.aggregate.call_args.kwargs,{'maxTimeMS':5000})
        self.assertEqual(pipeline[-1]['$facet']['summary'][0]['$match']['receivedDate']['$lte'],datetime(2026,3,15,23,59,59,999000,tzinfo=timezone.utc))
        self.assertNotIn('narrative',repr(pipeline));self.assertIn('$setDifference',repr(pipeline))

    def test_untrusted_sql_values_are_parameters_and_sql_totals_deduplicate_years(self):
        self.sql.execute.side_effect=[Mock(fetchall=lambda:[(1,'A','B',2021,4,2),(2,'A','B',2022,4,2)]),Mock(fetchone=lambda:(5,3))]
        result=vehicle_analytics(self.sql,self.database,make="A' OR 1=1",model='B',received_from=date(2026,1,1),received_to=date(2026,3,31))
        self.assertEqual(result['summary']['officialRecallCampaigns'],5)
        self.assertEqual(sum(row['officialRecallCampaigns']for row in result['modelYears']),8)
        for call in self.sql.execute.call_args_list:self.assertNotIn("A' OR 1=1",call.args[0]);self.assertIn("A' OR 1=1",call.args[1])

    def test_failures_are_sanitized_and_reader_closed(self):
        self.database.complaints.aggregate.side_effect=ExecutionTimeout('PRIVATE_DETAIL')
        result=self.client.get(self.query);self.assertEqual(result.status_code,503);self.assertNotIn('PRIVATE_DETAIL',result.get_data(as_text=True));self.sql.close.assert_called_once()
        self.connect.side_effect=OperationalError('PRIVATE_DETAIL');self.assertEqual(self.client.get(self.query).status_code,503)

    def test_analytics_is_read_only(self):
        self.assertEqual(self.client.post('/api/analytics/vehicle',json={}).status_code,405);self.connect.assert_not_called()


if __name__=='__main__':unittest.main()
