"""Owned browser-test actors and controlled case projection failures; never installed by normal Flask startup."""

from flask import g
from pymongo.errors import AutoReconnect

from backend.services.cases import CaseService, PostgresCaseRepository
from project_config import case_postgres, mongo_database, postgres
from scripts.support.local_api import LocalApi


def prepare_case_fixtures(app, base_url, emails, password, pending_note):
    users = []
    for email in emails[2:5]:
        client = LocalApi(base_url)
        client.request('/api/auth/csrf')
        user = client.request('/api/auth/register', {'email': email, 'password': password}, method='POST')['user']
        users.append(user)
        client.request('/api/auth/logout', {}, method='POST')
    with postgres() as connection:
        for user, role in zip(users, ['ANALYST', 'ANALYST', 'ADMIN'], strict=True):
            connection.execute('UPDATE app_user SET role=%s WHERE user_id=%s', (role, user['userId']))
    owners = {user['userId'] for user in users}
    owned_cases = set()
    faults = {'replace': 2, 'delete': 1}

    class OwnedRepository(PostgresCaseRepository):
        def enqueue(self, operation_id, actor, row, *args):
            if row['created_by'] in owners:
                owned_cases.add(row['case_id'])
            return super().enqueue(operation_id, actor, row, *args)

    class ControlledCollection:
        def __init__(self, collection):
            self.collection = collection

        def __getattr__(self, name):
            return getattr(self.collection, name)

        def replace_one(self, selector, document, **kwargs):
            if (document['caseId'] in owned_cases and faults['replace'] and
                    any(note['text'] == pending_note for note in document['notes'])):
                faults['replace'] -= 1
                raise AutoReconnect('Owned browser fixture: interrupted projection')
            return self.collection.replace_one(selector, document, **kwargs)

        def delete_one(self, selector, **kwargs):
            if selector.get('caseId') in owned_cases and faults['delete']:
                faults['delete'] -= 1
                raise AutoReconnect('Owned browser fixture: interrupted deletion')
            return self.collection.delete_one(selector, **kwargs)

    class ControlledDatabase:
        def __init__(self, database):
            self.case_details = ControlledCollection(database.case_details)
            self.complaints = database.complaints

    def factory():
        g.case_postgres = case_postgres()
        return CaseService(OwnedRepository(g.case_postgres), ControlledDatabase(mongo_database(app.extensions['mongo_client'])))

    app.config['CASE_SERVICE_FACTORY'] = factory
    return {'analystId': users[0]['userId'], 'otherAnalystId': users[1]['userId'], 'adminId': users[2]['userId'], 'pendingNote': pending_note}
