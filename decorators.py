# utils/decorators.py
from functools import wraps
from flask import redirect, url_for, session, jsonify, request

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Admin access required', 'redirect': '/admin/login'}), 401
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

def require_hr(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_hr'):
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'HR access required', 'redirect': '/login'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def require_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'email' not in session:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Login required', 'redirect': '/login'}), 401
            return redirect('/login')
        
        # Ensure it's a regular user (not HR or Admin)
        if session.get('is_hr') or session.get('is_admin'):
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'User access only', 'redirect': '/login'}), 403
            return redirect('/login')
        
        return f(*args, **kwargs)
    return decorated_function

def require_manual_verifier(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_manual_verifier'):
            return redirect(url_for('manual_verification.manual_verifier_login'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Login required', 'redirect': '/login'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Alias for backward compatibility
hr_required = require_hr