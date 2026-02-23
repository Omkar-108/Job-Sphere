# services/auth_service.py
import time
from datetime import datetime
from flask import session
from database.repository import user_repo, hr_repo
from database.setup import db
import logging
from services.email_service import email_service
from services.verification_service import verification_service

logger = logging.getLogger(__name__)

class AuthService:
    # def __init__(self):  # ADD INIT METHOD
    #     self.verification_service = verification_service
    
    @staticmethod
    def authenticate_user(identifier: str, password: str):
        """Authenticate user, HR, or admin with OTP for HR/User"""
        
        # HR authentication
        hr = hr_repo.find_by_email_or_username(identifier)
        if hr:
            # Compare plain text passwords directly
            password_match = password == hr.password
        
        if hr and password_match:
            # STORE PENDING LOGIN IN SESSION FOR OTP
            session['pending_login'] = {
                'type': 'hr',
                'id': str(hr._id),
                'email': hr.email,
                'username': hr.username
            }
            
            if hr.email != identifier:
                identifier = hr.email  # Use email for OTP sending
            # GENERATE AND SEND OTP
            otp = verification_service.generate_and_send_otp(identifier)
            if otp:
                return {'otp_required': True, 'message': 'OTP sent to your email.'}
            else:
                return {'error': 'Failed to send OTP email. Please try again.'}
        
        # User authentication
        user = user_repo.find_by_email(identifier) or user_repo.find_by_username(identifier)
        if user:
            # Compare plain text passwords directly
            password_match = password == user.password
            print(f"User found: {user.email}, Password match: {password_match}")
            print(f"Provided password: {password}, Stored password: {user.password}")
        
        if user and password_match:
            # STORE PENDING LOGIN IN SESSION FOR OTP
            session['pending_login'] = {
                'type': 'user',
                'id': str(user._id),
                'email': user.email,
                'username': user.username
            }

            if user.email != identifier:
                identifier = user.email  # Use email for OTP sending
            
            # GENERATE AND SEND OTP
            otp = verification_service.generate_and_send_otp(identifier)
            if otp:
                return {'otp_required': True, 'message': 'OTP sent to your email.'}
            else:
                return {'error': 'Failed to send OTP email. Please try again.'}
        
        # Admin authentication (NO OTP required)
        admin_data = None
        if db is not None and hasattr(db, 'admin') and db.admin is not None:
            # Check plain text password directly
            admin_data = db.admin.find_one({'email': identifier, 'password': password})
            
        if admin_data:
            return {
                'type': 'admin',
                'data': admin_data,
                'session_data': {
                    'is_admin': True,
                    'is_hr': False,
                    'admin_email': admin_data["email"],
                    'admin_id': str(admin_data["_id"])
                }
            }
        
        return {'error': 'Invalid credentials'}
    
    @staticmethod
    def verify_otp_and_complete_login(otp: str):  # ADD THIS NEW METHOD
        """Verify OTP and complete login"""
        pending = session.get('pending_login')
        sent_time = session.get('otp_sent_time')
        
        if not pending or not sent_time:
            return {'error': 'No OTP session found. Please login again.'}
        
        # Check OTP expiration
        if verification_service.is_otp_expired(sent_time):
            return {'error': 'OTP expired. Please login again.'}
        
        # Verify OTP
        if not verification_service.verify_otp(otp):
            return {'error': 'Invalid OTP. Please try again.'}
        
        # OTP valid, complete login based on type
        if pending['type'] == 'hr':
            hr = hr_repo.find_by_id(pending['id'])
            if not hr:
                return {'error': 'HR not found'}
            
            return {
                'type': 'hr',
                'session_data': {
                    'is_hr': True,
                    'is_admin': False,
                    'email': hr.email,
                    'username': hr.username,
                    'hr_id': pending['id']
                }
            }
        
        elif pending['type'] == 'user':
            user = user_repo.find_by_id(pending['id'])
            if not user:
                return {'error': 'User not found'}
            
            return {
                'type': 'user',
                'session_data': {
                    'is_hr': False,
                    'is_admin': False,
                    'email': user.email,
                    'username': user.username,
                    'user_id': pending['id']
                }
            }
        
        return {'error': 'Unknown login type.'}
    
    @staticmethod
    def register_user(username: str, email: str, password: str):
        """Register a new user"""
        from database.models import User
        
        # Check if email exists
        if user_repo.find_by_email(email) or hr_repo.find_by_email_or_username(email):
            return {'error': 'Email already in use'}
        
        # Check if username exists
        if user_repo.find_by_username(username):
            return {'error': 'Username already exists'}
        
        # Create user
        user = User(
            username=username,
            email=email,
            password=password
        )
        
        user_id = user_repo.create(user)
        return {'success': True, 'user_id': user_id}
    
    @staticmethod
    def logout():
        """Clear session including OTP data"""
        session.pop('pending_login', None)
        session.pop('otp_sent_time', None)
        session.pop('manual_verifier_otp', None)
        session.pop('manual_verifier_email', None)
        session.clear()
        return True

# Service instance
auth_service = AuthService()