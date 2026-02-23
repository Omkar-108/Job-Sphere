# routes/auth_routes.py
from fastapi import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from services.auth_service import auth_service
import time  # ADD THIS IMPORT
from services import towstepverification, email_service, emailsent # ADD THIS IMPORT

auth_bp = Blueprint('auth', __name__)

# reCAPTCHA Configuration
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "").strip()
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "").strip()
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_recaptcha(token):
    """Verify reCAPTCHA token with Google"""
    if not token:
        return {"success": False, "error": "Missing token"}

    try:
        response = requests.post(
            RECAPTCHA_VERIFY_URL,
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": token
            },
            timeout=5
        )
        return response.json()
    except Exception as e:
        print("reCAPTCHA verification error:", str(e))
        return {"success": False, "error": "Verification failed"}

@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html',site_key=RECAPTCHA_SITE_KEY)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or request.form
    identifier = (data.get('email') or "").strip()
    password = (data.get('password') or "").strip()
    recaptcha_token = data.get("g-recaptcha-response")

    print(f"[DEBUG] Login attempt - Identifier: {identifier}, Password length: {len(password)}")

    if not identifier or not password:
        return jsonify({"error": "Email/Username and password required"}), 400
    if not recaptcha_token:
        return jsonify({"error": "reCAPTCHA token is required"}), 400
    recaptcha_result = verify_recaptcha(recaptcha_token)
    print(f"[DEBUG] reCAPTCHA result: {recaptcha_result}")
    if not recaptcha_result.get("success"):
        return jsonify({"error": "reCAPTCHA verification failed"}), 400
    auth_result = auth_service.authenticate_user(identifier, password)
    print(f"[DEBUG] Auth result: {auth_result}")
    
    # =========== CHANGES START HERE ===========
    if 'error' in auth_result:
        print(f"[DEBUG] Authentication error: {auth_result['error']}")
        return jsonify({"error": auth_result['error']}), 401
    
    # If OTP required for HR/User
    if 'otp_required' in auth_result:
        return jsonify(auth_result)
    
    # If admin login (no OTP)
    if auth_result['type'] == 'admin':
        for key, value in auth_result['session_data'].items():
            session[key] = value
        return jsonify({"redirect": url_for('admin.admin_dashboard')})
    
    # This should not be reached if OTP is implemented correctly
    return jsonify({"error": "Authentication failed"}), 401
    # =========== CHANGES END HERE ===========

@auth_bp.route('/api/verify-otp', methods=['POST'])  # ADD THIS NEW ROUTE
def verify_otp():
    data = request.get_json(silent=True) or request.form
    otp = (data.get('otp') or '').strip()
    
    if not otp:
        return jsonify({"error": "OTP is required"}), 400
    
    # Check pending login session
    pending = session.get('pending_login')
    print("auth_service pending:",pending)
    sent_time = session.get('otp_sent_time')
    
    if not pending or not sent_time:
        return jsonify({"error": "No OTP session found. Please login again."}), 400
    
    # Check OTP expiration (30 seconds)
    if int(time.time()) - int(sent_time) > 30:
        return jsonify({"error": "OTP expired. Please login again."}), 400
    
    # Verify OTP
    if not towstepverification.verify_otp(otp):
        return jsonify({"error": "Invalid OTP. Please try again."}), 401
    
    # OTP valid, complete login
    if pending['type'] == 'hr':
        # Get HR data again to ensure fresh data
        from database.repository import hr_repo
        hr = hr_repo.find_by_email_or_username(pending['email'])
        print("from auth_routes:",hr)
        if not hr:
            return jsonify({"error": "HR account not found"}), 400
        
        # Set session data
        session['is_hr'] = True
        session['is_admin'] = False
        session['email'] = pending['email']
        session['username'] = pending['username']
        session['hr_id'] = pending['id']
        
        # Clear OTP session
        session.pop('pending_login', None)
        session.pop('otp_sent_time', None)
        
        return jsonify({"redirect": url_for('hr.dashboard_hr')})
    
    elif pending['type'] == 'user':
        # Get User data again
        from database.repository import user_repo
        print("pending id:",pending['id'])
        user = user_repo.find_by_email_or_username(pending['email'])
        print("from auth_routes:",user)
        if not user:
            return jsonify({"error": "User account not found"}), 400
        
        # Set session data
        session['is_hr'] = False
        session['is_admin'] = False
        session['email'] = pending['email']
        session['username'] = pending['username']
        session['user_id'] = pending['id']
        
        # Clear OTP session
        session.pop('pending_login', None)
        session.pop('otp_sent_time', None)
        
        return jsonify({"redirect": url_for('user.dashboard_user')})
    
    return jsonify({"error": "Unknown login type"}), 400

@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@auth_bp.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json(silent=True) or request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    result = auth_service.register_user(username, email, password)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify({"message": "Account created successfully!", "redirect": "/login"})

@auth_bp.route('/logout')
def logout():
    # Clear OTP session data too
    session.pop('pending_login', None)
    session.pop('otp_sent_time', None)
    auth_service.logout()
    return redirect(url_for('auth.login_page'))