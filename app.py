from config import app
from models import inject_globals, from_json_filter, parse_amenities_filter

import routes.main_routes
import routes.auth_routes
import routes.booking_routes
import routes.user_routes
import routes.admin_routes
import routes.api_routes

app.config['WTF_CSRF_ENABLED'] = True
app.context_processor(inject_globals)

app.jinja_env.filters['from_json'] = from_json_filter
app.jinja_env.filters['parse_amenities'] = parse_amenities_filter

@app.template_filter('contains')
def contains_filter(value, substring):
    """Custom filter untuk cek substring"""
    return substring.lower() in str(value).lower()

@app.template_filter('contains_case')
def contains_case_filter(value, substring):
    """Custom filter untuk cek substring (case-sensitive)"""
    return substring in str(value)

if __name__ == '__main__':
    app.run(debug=True, port=5000)