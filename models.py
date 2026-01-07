from functools import wraps
from flask import session, flash, redirect, url_for, request
import json
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from config import app

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor
def inject_globals():
    from datetime import datetime
    return {
        'current_year': datetime.now().year,
        'site_name': 'Feizen Haven'
    }

# Custom Jinja2 Filters
def from_json_filter(value):
    """Convert JSON string to Python object"""
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

def parse_amenities_filter(value):
    """Parse amenities JSON and return list"""
    if value:
        try:
            amenities = json.loads(value)
            if isinstance(amenities, list):
                return amenities
        except:
            pass
    return []

