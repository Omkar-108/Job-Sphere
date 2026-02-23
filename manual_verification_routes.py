# routes/manual_verification_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.verification_service import verification_service
from utils.decorators import require_manual_verifier

manual_verification_bp = Blueprint('manual_verification', __name__)

@manual_verification_bp.route('/manual-verification', methods=['GET', 'POST'])
def manual_verifier_login():
    """Manual verifier login page"""
    if request.method == 'GET':
        return render_template('manual_verification.html')
    
    # POST: handle login
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    
    result = verification_service.manual_verifier_login(email, password)
    
    if 'error' in result:
        return render_template('manual_verification.html', error=result['error'])
    elif 'otp_sent' in result:
        return render_template('manual_verification.html', otp_sent=True, email=email)

@manual_verification_bp.route('/manual-verification/otp', methods=['GET', 'POST'])
def manual_verifier_otp():
    """Manual verifier OTP verification"""
    if request.method == 'GET':
        otp = request.args.get('otp', '').strip()
    else:
        otp = request.form.get('otp', '').strip()
    
    email = session.get('manual_verifier_email')
    
    if not email or not otp:
        return render_template('manual_verification.html', error='Session expired or invalid OTP.')
    
    if not verification_service.verify_manual_verifier_otp(otp):
        return render_template('manual_verification.html', otp_sent=True, email=email, error='Invalid OTP.')
    
    session['is_manual_verifier'] = True
    return redirect(url_for('manual_verification.manual_verifier_dashboard'))

@manual_verification_bp.route('/manual-verification/dashboard')
@require_manual_verifier
def manual_verifier_dashboard():
    """Manual verification dashboard"""
    pending = verification_service.get_pending_registrations()
    return render_template('manual_verification_dashboard.html', pending=pending)

@manual_verification_bp.route('/manual-verification/approve/<string:pending_id>', methods=['POST'])
@require_manual_verifier
def manual_verifier_approve(pending_id):
    """Approve a pending registration"""
    result = verification_service.approve_registration(pending_id)
    
    if 'error' in result:
        flash(result['error'], 'error')
    else:
        flash('Registration approved successfully!', 'success')
    
    return redirect(url_for('manual_verification.manual_verifier_dashboard'))

@manual_verification_bp.route('/manual-verification/reject/<string:pending_id>', methods=['POST'])
@require_manual_verifier
def manual_verifier_reject(pending_id):
    """Reject a pending registration"""
    result = verification_service.reject_registration(pending_id)
    
    if 'error' in result:
        flash(result['error'], 'error')
    else:
        flash('Registration rejected successfully!', 'success')
    
    return redirect(url_for('manual_verification.manual_verifier_dashboard'))