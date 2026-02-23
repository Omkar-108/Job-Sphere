# services/verification_service.py
import secrets
import time
import os
from flask import session
from bson import ObjectId
from .email_service import email_service
import services.towstepverification as towstepverification

class VerificationService:
    def __init__(self, mongo):
        self.mongo = mongo
    
    def generate_and_send_otp(self, email):
        """Generate OTP and send it via email"""
        otp = towstepverification.generate_otp()
        print(f"[VerificationService] OTP for {email}: {otp}")
        
        if email_service.send_otp_email(email, otp):
            session['otp_sent_time'] = int(time.time())
            return otp
        return None
    
    def verify_otp(self, otp):
        """Verify OTP using towstepverification module"""
        return towstepverification.verify_otp(otp)
    
    def is_otp_expired(self, sent_time):
        """Check if OTP is expired (30 seconds)"""
        if not sent_time:
            return True
        return int(time.time()) - int(sent_time) > 30
    
    # Manual verification methods
    def manual_verifier_login(self, email, password):
        """Authenticate manual verifier"""
        allowed_email = os.getenv('VERIFIER_EMAIL', 'verifier@example.com')
        allowed_password = os.getenv('VERIFIER_PASSWORD', 'secure_password_here')
        
        if email != allowed_email:
            return {'error': 'Invalid email for manual verification.'}
        if password != allowed_password:
            return {'error': 'Incorrect password.'}
        
        # Generate OTP for verifier
        otp = secrets.randbelow(900000) + 100000
        session['manual_verifier_otp'] = str(otp)
        session['manual_verifier_email'] = email
        
        # Send OTP email
        if email_service.send_otp_email(email, f"Your OTP for manual verification login is: {otp}"):
            return {'otp_sent': True, 'email': email}
        else:
            return {'error': 'Failed to send OTP email.'}
    
    def verify_manual_verifier_otp(self, otp):
        """Verify manual verifier OTP"""
        stored_otp = session.get('manual_verifier_otp')
        email = session.get('manual_verifier_email')
        
        if not email or not otp or not stored_otp:
            return False
        
        if otp != stored_otp:
            return False
        
        # Clear OTP after successful verification
        session.pop('manual_verifier_otp', None)
        return True
    
    def get_pending_registrations(self):
        """Get all pending admin registrations"""
        pending = list(self.mongo.pending_admin_registrations.find().sort('submitted_at', -1))
        
        # Convert ObjectId to string
        for reg in pending:
            reg['_id'] = str(reg['_id'])
            if 'submitted_at' in reg and isinstance(reg['submitted_at'], time.struct_time):
                reg['submitted_at'] = time.strftime('%Y-%m-%d %H:%M:%S', reg['submitted_at'])
        
        return pending
    
    def approve_registration(self, pending_id):
        """Approve a pending admin registration"""
        reg = self.mongo.pending_admin_registrations.find_one({'_id': ObjectId(pending_id)})
        if not reg:
            return {'error': 'Registration not found'}
        
        try:
            # Insert company
            company_data = {
                'company_name': reg['company_name'],
                'company_email': reg['company_email'],
                'company_website': reg['company_website'],
                'company_address': reg['company_address'],
                'company_phone': reg['company_phone'],
                'industry': reg['industry'],
                'company_size': reg['company_size'],
                'verified': True,
                'pending_review': False,
                'created_at': time.time()
            }
            
            company_result = self.mongo.company.insert_one(company_data)
            company_id = str(company_result.inserted_id)
            
            # Insert admin
            admin_data = {
                'name': reg['admin_name'],
                'email': reg['admin_email'],
                'password': reg['password'],
                'company_id': company_id,
                'verified': True,
                'created_at': time.time()
            }
            
            self.mongo.admin.insert_one(admin_data)
            
            # Send approval email
            email_service.send_otp_email(
                reg['admin_email'],
                f"Your admin registration for {reg['company_name']} has been approved. You may now log in."
            )
            
            # Delete from pending
            self.mongo.pending_admin_registrations.delete_one({'_id': ObjectId(pending_id)})
            
            return {'success': True}
            
        except Exception as e:
            print(f"[VerificationService] Error approving registration: {e}")
            return {'error': f'Failed to approve registration: {str(e)}'}
    
    def reject_registration(self, pending_id):
        """Reject a pending admin registration"""
        reg = self.mongo.pending_admin_registrations.find_one({'_id': ObjectId(pending_id)})
        if not reg:
            return {'error': 'Registration not found'}
        
        try:
            # Send rejection email
            email_service.send_otp_email(
                reg['admin_email'],
                f"Your admin registration for {reg['company_name']} was rejected. Please contact support for more information."
            )
            
            # Delete from pending
            self.mongo.pending_admin_registrations.delete_one({'_id': ObjectId(pending_id)})
            
            return {'success': True}
            
        except Exception as e:
            print(f"[VerificationService] Error rejecting registration: {e}")
            return {'error': f'Failed to reject registration: {str(e)}'}
# Create singleton instance
verification_service = VerificationService(mongo=None)  # Pass actual mongo instance when initializing