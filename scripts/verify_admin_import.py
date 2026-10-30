"""Verify the admin terminal helper with real auth and isolated real ETL fixtures."""

import hashlib
import io
import json
import secrets
import shutil
import sys
import threading
import zipfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo.errors import BulkWriteError
from psycopg import sql
from werkzeug.serving import make_server
from backend import create_app
from etl.runner import IMPORT_LOCK, ImportBusy
from etl.source import SOURCES
from mongodb.schema import initialize
from project_config import ROOT, mongo_client, mongo_database, postgres
from scripts import admin_import
from scripts.benchmark_databases import owned_namespace
from scripts.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_cases import snapshot


def make_archives(folder):
    recall=['']*29
    for index,value in {0:'fixture-row-1',1:'26VTEST001',2:'VERIFYMAKE',3:'VERIFYMODEL',4:'2022',
                        6:'STEERING',7:'VERIFIER MANUFACTURER',10:'V',11:'4',14:'VERIFIER MANUFACTURER',
                        15:'20260101',19:'Fixture recall',20:'Fixture consequence',21:'Fixture remedy',27:'N',28:'N'}.items():recall[index]=value
    investigation=['PE26001','VERIFYMAKE','VERIFYMODEL','2022','STEERING','VERIFIER MANUFACTURER',
                   '20260102','','26VTEST001','Fixture investigation','Fixture summary']
    first=['']*51
    for index,value in {0:'501',1:'999000001',2:'VERIFIER MANUFACTURER',3:'VERIFYMAKE',4:'VERIFYMODEL',5:'2022',
                        6:'N',7:'20240101',8:'N',9:'0',10:'0',11:'STEERING',16:'20240102',17:'10',18:'1',
                        19:'Synthetic fixture allegation',45:'V'}.items():first[index]=value
    second=first.copy();second[0]='502';second[11]='ELECTRICAL SYSTEM'
    third=first.copy();third[0]='503';third[1]='999000002';third[7]='20260101';third[16]='20260102'
    rows={'recalls':[recall],'investigations':[investigation],
          'complaints_2020_2024':[first,second],'complaints_2025_2026':[third]}
    profile={}
    for key,(filename,_) in SOURCES.items():
        path=folder/filename
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(key+'.txt','\n'.join('\t'.join(row) for row in rows[key])+'\n')
        profile[key]={'filename':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    path=folder/'profile.json';path.write_text(json.dumps({'sources':profile}),encoding='utf-8')
    return path


def main():
    token=uuid4().hex;namespace='bench_'+token
    owned_namespace(namespace,namespace)
    directory=ROOT/'docs/admin_import'/(datetime.now().strftime('%Y%m%dT%H%M%S')+'-'+token[:8])
    directory.mkdir(parents=True,exist_ok=False)
    raw=ROOT/'data/logs'/('admin-import-native-'+token);raw.mkdir(parents=True)
    profile=make_archives(raw)
    before=snapshot()
    with postgres() as c:original_audit_count=c.execute('SELECT count(*) FROM public.data_import_log').fetchone()[0]
    report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'successful':False,'checks':[],
            'scope':'Real localhost auth and CLI main/controller with actual ETL, owned SQL schema and MongoDB database, and five synthetic raw rows. No full production-data import.',
            'fixture_namespace':namespace,'fixture_schema_removed':False,'fixture_database_removed':False}
    emails=['admin-import-'+token+'-'+suffix+'@example.invalid' for suffix in ['admin','normal','analyst']]
    password=secrets.token_urlsafe(24)
    app=create_app();server=make_server('127.0.0.1',0,app,threaded=True,request_handler=QuietHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    client=mongo_client();database=client[namespace];created=False;fixture_db_created=False
    last_cli_clients=[]
    controller=admin_import.run_authorized_import

    def check(condition,message):
        if not condition:raise AssertionError(message)
        report['checks'].append(message)

    def owned_pg():
        return postgres(options='-c search_path='+namespace+',pg_catalog')

    class OwnedMongo:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def __getitem__(self,name):return database

    def flow(api,confirm):
        return controller(api,confirm,preflight=partial(admin_import.approved_sources,raw=raw,profile_path=profile),
                 pg_factory=owned_pg,mongo_factory=OwnedMongo)

    def login(index):
        api=LocalApi(base);api.request('/api/auth/csrf')
        api.request('/api/auth/login',{'email':emails[index],'password':password},method='POST')
        return api

    def expect(kind,action,label):
        try:action()
        except kind:check(True,label)
        else:raise AssertionError(label)

    def audit():
        with owned_pg() as c:
            return c.execute('SELECT dataset_name,status,records_inserted,records_updated,error_summary FROM data_import_log ORDER BY import_id').fetchall()

    def invoke_cli(index,confirmation):
        def factory(origin):
            api=LocalApi(origin);last_cli_clients.append(api);return api
        out=io.StringIO()
        with patch('scripts.admin_import.LocalApi',side_effect=factory),patch('scripts.admin_import.run_authorized_import',side_effect=flow),patch('builtins.input',side_effect=[emails[index],confirmation]),patch('getpass.getpass',return_value=password),redirect_stdout(out):
            code=admin_import.main(['--base-url',base])
        check(password not in out.getvalue(),'CLI output excludes its hidden password')
        try:last_cli_clients[-1].request('/api/auth/me')
        except ApiError as error:check(error.status==401,'CLI finally revokes its own application session')
        else:raise AssertionError('CLI left an authenticated helper session')
        return code,out.getvalue()

    try:
        report['real_approved_archives_read_only']=admin_import.approved_sources()
        check(len(report['real_approved_archives_read_only'])==4,'Actual four local archives match the inspected profile; checked without importing')
        ids=[]
        for email in emails:
            api=LocalApi(base);api.request('/api/auth/csrf')
            ids.append(api.request('/api/auth/register',{'email':email,'password':password},method='POST')['user']['userId'])
            api.request('/api/auth/logout',{},method='POST')
        with postgres() as c:
            for index,role in [(0,'ADMIN'),(2,'ANALYST')]:
                c.execute('UPDATE public.app_user SET role=%s WHERE user_id=%s AND email=%s',(role,ids[index],emails[index]))
            c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(namespace)))
        created=True
        with owned_pg() as c:
            c.execute((ROOT/'sql/schema.sql').read_text(encoding='utf-8'),prepare=False)
            c.execute((ROOT/'sql/views.sql').read_text(encoding='utf-8'),prepare=False)
        initialize(database);fixture_db_created=True
        with patch('etl.source.RAW',raw):
            expect(admin_import.AdminImportDenied,lambda:flow(LocalApi(base),lambda _:True),'Signed-out controller request cannot initiate an import')
            for index in (1,2):
                code,_=invoke_cli(index,'IMPORT')
                check(code==1,'Normal/analyst CLI sign-in is denied before ETL')
            code,_=invoke_cli(0,'CANCEL');check(code==0 and not audit(),'Cancelled confirmation runs no stages or audit writes')
            admin=login(0)
            try:
                with postgres() as holder:
                    holder.execute('SELECT pg_advisory_lock(%s)',(IMPORT_LOCK,));holder.commit()
                    try:expect(ImportBusy,lambda:flow(admin,lambda _:True),'An existing project importer lock refuses a second import')
                    finally:holder.execute('SELECT pg_advisory_unlock(%s)',(IMPORT_LOCK,));holder.commit()
                def revoke(_):
                    with postgres() as c:c.execute("UPDATE public.app_user SET role='NORMAL_USER' WHERE user_id=%s AND email=%s",(ids[0],emails[0]))
                    return True
                expect(admin_import.AdminImportDenied,lambda:flow(admin,revoke),'Fresh role lookup blocks access revoked during confirmation')
                with postgres() as c:c.execute("UPDATE public.app_user SET role='ADMIN' WHERE user_id=%s AND email=%s",(ids[0],emails[0]))
                expired=login(0)
                def sign_out(_):
                    expired.request('/api/auth/logout',{},method='POST')
                    return True
                expect(admin_import.AdminImportDenied,lambda:flow(expired,sign_out),'Fresh session lookup blocks sign-out during confirmation')
                saved_profile=profile.read_bytes();content=json.loads(saved_profile);content['sources']['recalls']['sha256']='0'*64;profile.write_text(json.dumps(content))
                expect(admin_import.SourceSnapshotMismatch,lambda:flow(admin,lambda _:True),'Mismatched approved snapshot refuses import before any stage')
                profile.write_bytes(saved_profile)
                check(not audit(),'Denied, busy and mismatched requests have no import stage audit rows')
            finally:admin.request('/api/auth/logout',{},method='POST')
            code,output=invoke_cli(0,'IMPORT');check(code==0,'The actual prompted admin CLI completes real isolated ETL')
            first=audit();check(len(first)==4 and all(row[1]=='COMPLETED' for row in first),'All four import stages log COMPLETED outcomes')
            with owned_pg() as c:
                counts={name:c.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(name))).fetchone()[0] for name in ['model_year','recall','official_investigation']}
            counts['complaints']=database.complaints.count_documents({})
            check(counts=={'model_year':1,'recall':1,'official_investigation':1,'complaints':2},'Actual SQL and MongoDB imports contain expected fixture entities')
            check(database.complaints.find_one({'_id':'999000001'})['components']==['ELECTRICAL SYSTEM','STEERING'],'Real complaint importer merges repeated component rows into one document')
            code,_=invoke_cli(0,'IMPORT');second=audit()[4:]
            check(code==0 and len(second)==4 and all(row[2]==0 for row in second),'Repeat CLI import refreshes entities without duplicate inserts')
            database.complaints.delete_one({'_id':'999000002'})
            database.command('collMod','complaints',validator={'$jsonSchema':{'required':['nativeFailureMarker']}},validationLevel='strict')
            code,failure_output=invoke_cli(0,'IMPORT');failed=audit()[-4:]
            check(code==1 and failed[-1][0:2]==('complaints','FAILED') and failed[-1][4]=='BulkWriteError','Actual MongoDB rejection produces a failed CLI exit and durable FAILED audit')
            check(all(row[1]=='COMPLETED' for row in failed[:-1]),'Earlier completed stages remain accurately recorded when a later stage fails')
            check('BulkWriteError' in failure_output and 'nativeFailureMarker' not in failure_output,'CLI failure prints the exception category without raw document diagnostics')
            with postgres() as c:
                acquired=c.execute('SELECT pg_try_advisory_lock(%s)',(IMPORT_LOCK,)).fetchone()[0]
                check(acquired,'Shared session lock is available after success and failure')
                if acquired:c.execute('SELECT pg_advisory_unlock(%s)',(IMPORT_LOCK,))
            report['fixture_import_counts']=counts
            report['fixture_audit_rows']=[{'dataset':row[0],'status':row[1],'inserted':row[2],'updated':row[3],'failure_category':row[4]} for row in audit()]
            report['console_success_example']=output
            report['console_failure_example']=failure_output
        with app.test_client() as web:
            page=web.get('/admin/imports')
            check(page.status_code==200 and b'scripts/admin_import.py' in page.data,'Import-history template serves the documented terminal entry point')
        report['native_checks_passed']=True
    except Exception as error:
        report['failure_type']=type(error).__name__
        if isinstance(error,AssertionError):report['assertion']=str(error)
    finally:
        server.shutdown();thread.join(timeout=5);server.server_close();app.extensions['mongo_client'].close()
        owned_namespace(namespace,namespace)
        with postgres() as c:
            if created:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(namespace)))
            c.execute('DELETE FROM public.app_user WHERE email=ANY(%s)',(emails,))
            report['fixture_schema_removed']=not c.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)',(namespace,)).fetchone()[0]
            report['existing_import_history_retained']=c.execute('SELECT count(*) FROM public.data_import_log').fetchone()[0]==original_audit_count
        if fixture_db_created:client.drop_database(namespace)
        report['fixture_database_removed']=namespace not in client.list_database_names();client.close()
        target=raw.resolve()
        if not target.is_relative_to((ROOT/'data/logs').resolve()) or target.name!='admin-import-native-'+token:
            raise RuntimeError('Unexpected native fixture cleanup target')
        shutil.rmtree(target)
        report['fixture_files_removed']=not target.exists()
        after=snapshot();report['existing_record_counts_retained']=before==after;report['record_counts']=after
        report['successful']=bool(report.get('native_checks_passed') and report['fixture_schema_removed'] and report['fixture_database_removed'] and report['fixture_files_removed'] and before==after and report['existing_import_history_retained'])
        report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        (directory/'native_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Admin import native checks:',len(report['checks']),'successful:',report['successful'])
    print('Evidence:',directory.relative_to(ROOT).as_posix())
    if not report['successful']:print('Failure category:',report.get('failure_type','cleanup/count mismatch'))
    return 0 if report['successful'] else 1


if __name__=='__main__':raise SystemExit(main())
