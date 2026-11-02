"""Admin read boundaries, monitoring DTOs and bounded/filter-parameterized queries."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from psycopg import OperationalError
from pymongo.errors import ExecutionTimeout

from backend import create_app
from backend.services.auth import token_hash
from tests.test_auth import MemoryAuthStore


class AdministrationTests(unittest.TestCase):
    def setUp(self):
        self.auth = MemoryAuthStore()
        self.sql = Mock()
        self.connect = Mock(return_value=self.sql)
        self.database = Mock()
        self.mongo = Mock(); self.mongo.__getitem__ = Mock(return_value=self.database)
        self.app = create_app({'TESTING':True,'SECRET_KEY':'test-only','DUMMY_PASSWORD_HASH':'unused',
                              'AUTH_STORE_FACTORY':lambda:self.auth,'PG_CONNECT':self.connect,
                              'MONGO_CLIENT_FACTORY':lambda:self.mongo})
        self.client = self.app.test_client()
        self.now = datetime.now(timezone.utc)
        self.row = (7,'complaints',self.now,self.now,617186,428837,0,0,0,'COMPLETED','a'*64+':'+ 'b'*64,False,None)

    def sign_in(self, role='ADMIN'):
        self.auth.users[1]={'userId':1,'email':'admin@example.test','role':role,'createdAt':self.now.isoformat()}
        token='t'*43
        self.auth.sessions[token_hash(token)]=(1,self.now+timedelta(hours=1))
        with self.client.session_transaction() as session:session['session_token']=token

    def test_anonymous_and_non_admins_cannot_read_monitoring(self):
        for role in [None,'NORMAL_USER','ANALYST']:
            if role:self.sign_in(role)
            for path in ['/api/admin/datasets','/api/admin/import-runs']:
                with self.subTest(role=role,path=path):self.assertEqual(self.client.get(path).status_code,401 if role is None else 403)
        self.connect.assert_not_called();self.database.complaints.count_documents.assert_not_called()

    def test_summary_counts_distinguish_campaigns_links_and_documents(self):
        self.sign_in()
        metrics=[('vehicle_catalogue',53555),('recalls',13600),('recall_vehicle',93743),('recall_record',219728),
                 ('investigations',3626),('investigation_vehicle',28647),('investigation_recall',1671),('schema_version',3)]
        self.sql.execute.side_effect=[Mock(fetchall=lambda:metrics),Mock(fetchall=lambda:[self.row])]
        self.database.complaints.count_documents.return_value=428837
        result=self.client.get('/api/admin/datasets')
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers['Cache-Control'],'no-store')
        items={item['key']:item for item in result.json['items']}
        self.assertEqual(items['complaints']['recordCount'],428837)
        self.assertEqual(items['recalls']['relationships'][1]['count'],219728)
        self.assertEqual(items['complaints']['latestRun']['recordsRead'],617186)
        self.assertIsNone(items['vehicle_catalogue']['latestRun'])
        self.assertEqual(len(items['complaints']['sourceArchives']),2)
        self.database.complaints.count_documents.assert_called_once_with({},maxTimeMS=5000)
        self.sql.close.assert_called_once()

    def test_import_filters_are_bound_and_pagination_is_bounded(self):
        self.sign_in();self.sql.execute.side_effect=[Mock(fetchone=lambda:(3,)),Mock(fetchall=lambda:[self.row])]
        result=self.client.get('/api/admin/import-runs?dataset=complaints&status=COMPLETED&page=2&pageSize=1')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['pagination'],{'page':2,'pageSize':1,'total':3,'totalPages':3})
        query,values=self.sql.execute.call_args.args
        self.assertNotIn('COMPLETED',query);self.assertNotIn('complaints',query)
        self.assertEqual(values,['complaints','COMPLETED',1,1])
        self.assertEqual(set(result.json['items'][0]),{'importId','dataset','startedAt','completedAt','recordsRead','recordsInserted','recordsUpdated','recordsSkipped','recordsRejected','status','sourceFingerprint','hasError','failureCategory'})
        self.assertNotIn('error_summary',query);self.database.complaints.count_documents.assert_not_called()

    def test_invalid_monitor_queries_do_not_open_reader(self):
        self.sign_in()
        paths=['/api/admin/datasets?page=1','/api/admin/import-runs?dataset=wrong','/api/admin/import-runs?status=done',
               '/api/admin/import-runs?status=FAILED&status=COMPLETED','/api/admin/import-runs?page=10001',
               '/api/admin/import-runs?pageSize=101','/api/admin/import-runs?page=0','/api/admin/import-runs?x=1',
               '/api/admin/import-runs?dataset=recalls%27%20OR%201=1']
        for path in paths:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,400)
        self.connect.assert_not_called()

    def test_running_run_allows_no_completion_or_fingerprint(self):
        self.sign_in()
        row=list(self.row);row[3]=None;row[9]='RUNNING';row[10]=None
        self.sql.execute.side_effect=[Mock(fetchone=lambda:(1,)),Mock(fetchall=lambda:[tuple(row)])]
        run=self.client.get('/api/admin/import-runs').json['items'][0]
        self.assertIsNone(run['completedAt']);self.assertIsNone(run['sourceFingerprint'])

    def test_sql_failure_is_sanitized(self):
        self.sign_in();self.connect.side_effect=OperationalError('DO_NOT_EXPOSE password')
        result=self.client.get('/api/admin/import-runs')
        self.assertEqual(result.status_code,503);self.assertNotIn('DO_NOT_EXPOSE',result.get_data(as_text=True))

    def test_mongo_timeout_is_sanitized_and_sql_is_closed(self):
        self.sign_in();self.sql.execute.return_value.fetchall.return_value=[]
        self.database.complaints.count_documents.side_effect=ExecutionTimeout('DO_NOT_EXPOSE')
        result=self.client.get('/api/admin/datasets')
        self.assertEqual(result.status_code,503);self.assertNotIn('DO_NOT_EXPOSE',result.get_data(as_text=True));self.sql.close.assert_called_once()

    def test_monitoring_endpoints_do_not_accept_writes(self):
        self.sign_in()
        for path in ['/api/admin/datasets','/api/admin/import-runs']:
            self.assertEqual(self.client.post(path,json={}).status_code,405)
        self.connect.assert_not_called()


if __name__=='__main__':unittest.main()
