"""HTML/API boundary, credential form safety and local assets without live databases."""

import unittest
from html.parser import HTMLParser
from unittest.mock import Mock

from backend import create_app


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms, self.scripts, self.labels, self.inputs = [], [], [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'form': self.forms.append(values)
        if tag == 'script': self.scripts.append(values)
        if tag == 'label' and 'for' in values: self.labels.append(values['for'])
        if tag == 'input': self.inputs.append(values)


class PageTests(unittest.TestCase):
    def setUp(self):
        self.sql = Mock(side_effect=AssertionError('HTML shells must not read databases'))
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'DO_NOT_RENDER_SIGNING_KEY', 'DUMMY_PASSWORD_HASH': 'unused',
                              'MONGO_CLIENT_FACTORY': Mock, 'PG_CONNECT': self.sql, 'AUTH_PG_CONNECT': self.sql,
                              'WORKFLOW_PG_CONNECT': self.sql})
        self.client = self.app.test_client()

    def test_home_is_html_and_api_discovery_is_json(self):
        home, discovery = self.client.get('/'), self.client.get('/api')
        self.assertEqual(home.status_code, 200)
        self.assertEqual(home.mimetype, 'text/html')
        self.assertIn('RecallScope', home.get_data(as_text=True))
        self.assertEqual(discovery.mimetype, 'application/json')
        self.assertIn('safetyProfile', discovery.json['links'])
        self.sql.assert_not_called()

    def test_all_page_shells_render_without_secrets_or_database_access(self):
        for path in ['/vehicles', '/vehicles/profile?year=2022&make=HONDA&model=CIVIC', '/login', '/register', '/saved-vehicles',
                     '/complaints', '/complaints/11426529', '/recalls/21V058000', '/investigations/EA15002', '/cases', '/cases/new', '/cases/123',
                     '/fleets', '/fleets/123', '/work-orders/123','/admin','/admin/users','/admin/imports','/analytics']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'text/html')
                self.assertNotIn('DO_NOT_RENDER_SIGNING_KEY', response.get_data(as_text=True))
        self.sql.assert_not_called()

    def test_private_page_shell_does_not_unlock_saved_vehicle_api(self):
        self.assertEqual(self.client.get('/saved-vehicles').status_code, 200)
        response = self.client.get('/api/saved-vehicles')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get('/cases/123').status_code, 200)
        self.assertEqual(self.client.get('/api/analysis-cases/123').status_code, 401)
        self.assertEqual(self.client.get('/fleets/123').status_code, 200)
        self.assertEqual(self.client.get('/api/fleets/123').status_code, 401)
        self.assertEqual(self.client.get('/work-orders/123').status_code, 200)
        self.assertEqual(self.client.get('/api/work-orders/123').status_code, 401)
        self.assertEqual(self.client.get('/admin').status_code, 200)
        self.assertEqual(self.client.get('/api/admin/datasets').status_code, 401)

    def test_credentials_cannot_fall_back_to_a_get_query_without_javascript(self):
        for page, target in [('/login', '/api/auth/login'), ('/register', '/api/auth/register')]:
            parser = FormParser(); parser.feed(self.client.get(page).get_data(as_text=True))
            form = next(item for item in parser.forms if item['id'] == 'auth-form')
            self.assertEqual(form['method'], 'post')
            self.assertEqual(form['action'], target)
            for field in [item for item in parser.inputs if item.get('id') in {'email', 'password'}]:
                self.assertIn(field['id'], parser.labels)
                self.assertIn('autocomplete', field)

    def test_html_csp_uses_local_scripts_and_prevents_embedding(self):
        response = self.client.get('/vehicles')
        policy = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn('unsafe-inline', policy)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        parser = FormParser(); parser.feed(response.get_data(as_text=True))
        self.assertTrue(parser.scripts)
        self.assertTrue(all(item.get('src', '').startswith('/static/') for item in parser.scripts))

    def test_local_assets_are_served_and_query_markup_is_not_rendered_as_html(self):
        for name in ['app.css', 'app.js', 'api.js', 'ui.js', 'research.js', 'cases.js', 'fleets.js', 'admin.js', 'analytics.js', 'mark.svg']:
            with self.client.get('/static/' + name) as response:
                self.assertEqual(response.status_code, 200)
        attack = '<script>DO_NOT_EXECUTE</script>'
        for path in ['/vehicles', '/vehicles/profile', '/login', '/complaints', '/complaints/123', '/recalls/ABC', '/investigations/ABC', '/cases/new', '/cases/123', '/fleets', '/fleets/123', '/work-orders/123']:
            response = self.client.get(path, query_string={'make': attack, 'next': attack})
            self.assertNotIn(attack, response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
