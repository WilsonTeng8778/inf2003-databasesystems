"""HTML shells; browser code uses the existing same-origin, permission-checked APIs."""

from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)


@pages.after_request
def page_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


@pages.get('/')
@pages.get('/vehicles')
def search():
    return render_template('search.html', page='search', title='Vehicle search')


@pages.get('/vehicles/profile')
def profile():
    return render_template('profile.html', page='profile', title='Vehicle safety profile')


@pages.get('/complaints')
def complaint_explorer():
    return render_template('complaints.html', page='complaints', title='Complaint explorer')


@pages.get('/complaints/<identifier>')
def complaint_record(identifier):
    return render_template('record.html', page='record', title='Consumer complaint', kind='complaints')


@pages.get('/recalls/<identifier>')
def recall_record(identifier):
    return render_template('record.html', page='record', title='Official recall', kind='recalls')


@pages.get('/investigations/<identifier>')
def investigation_record(identifier):
    return render_template('record.html', page='record', title='Official investigation', kind='investigations')


@pages.get('/login')
def login():
    return render_template('auth.html', page='login', title='Sign in', registering=False)


@pages.get('/register')
def register():
    return render_template('auth.html', page='register', title='Create an account', registering=True)


@pages.get('/saved-vehicles')
def saved():
    return render_template('saved.html', page='saved', title='My vehicles')


@pages.get('/cases')
def case_list():
    return render_template('cases.html', page='cases', title='Analyst cases', case_view='list')


@pages.get('/cases/new')
def case_new():
    return render_template('case_new.html', page='cases', title='New analyst case', case_view='new')


@pages.get('/cases/<int:case_id>')
def case_detail(case_id):
    return render_template('case_detail.html', page='cases', title='Analyst case', case_view='detail')


@pages.get('/fleets')
def fleet_list():
    return render_template('fleets.html', page='fleets', title='My fleets', fleet_view='list')


@pages.get('/fleets/<int:fleet_id>')
def fleet_detail(fleet_id):
    return render_template('fleet_detail.html', page='fleets', title='Fleet recall tracking', fleet_view='detail')


@pages.get('/work-orders/<int:order_id>')
def work_order(order_id):
    return render_template('work_order.html', page='fleets', title='Recall work order', fleet_view='order')


@pages.get('/admin')
def admin_overview():
    return render_template('admin_overview.html', page='admin', title='Dataset administration', admin_view='overview')


@pages.get('/admin/users')
def admin_users():
    return render_template('admin_users.html', page='admin', title='User roles', admin_view='users')


@pages.get('/admin/imports')
def admin_imports():
    return render_template('admin_imports.html', page='admin', title='Import history', admin_view='imports')


@pages.get('/analytics')
def analytics_dashboard():
    return render_template('analytics.html',page='analytics',title='Vehicle analytics')
