# services/admin_service.py
from datetime import datetime
from database.repository import hr_repo
from database.models import HR
from database.setup import db
import logging

logger = logging.getLogger(__name__)

class AdminService:
    @staticmethod
    def add_hr(hr_data: dict):
        """Add new HR"""
        # Check if email exists
        existing_email = db.hr.find_one({'email': hr_data['email']}) or \
                        db.users.find_one({'email': hr_data['email']}) or \
                        db.admin.find_one({'email': hr_data['email']})
        
        if existing_email:
            return {'error': 'Email already used by another account'}
        
        # Check unique username
        if hr_repo.find_by_email_or_username(hr_data['username']):
            return {'error': 'Username already exists'}
        
        # Create HR
        hr = HR(
            username=hr_data['username'],
            name=hr_data['name'],
            email=hr_data['email'],
            password=hr_data['password'],
            department=hr_data['department']
        )
        
        hr_id = hr_repo.create(hr)
        return {'success': True, 'hr_id': hr_id}
    
    @staticmethod
    def update_hr(hr_id: str, hr_data: dict):
        """Update HR details"""
        # Check username duplicate (excluding current HR)
        existing_user = db.hr.find_one({
            'username': hr_data['username'],
            '_id': {'$ne': hr_id}
        })
        
        if existing_user:
            return {'error': 'Username already in use'}
        
        # Check email duplicate (excluding current HR)
        existing_email = db.hr.find_one({
            'email': hr_data['email'],
            '_id': {'$ne': hr_id}
        })
        
        if existing_email:
            return {'error': 'Email already in use'}
        
        # Prepare update data
        update_data = {
            'username': hr_data['username'],
            'name': hr_data['name'],
            'department': hr_data['department'],
            'email': hr_data['email']
        }
        
        if hr_data.get('password', '').strip():
            update_data['password'] = hr_data['password']
        
        success = hr_repo.update(hr_id, update_data)
        return {'success': success}
    
    @staticmethod
    def delete_hr(hr_id: str):
        """Delete HR"""
        success = hr_repo.delete(hr_id)
        return {'success': success}
    
    @staticmethod
    def get_all_hr(search: str = None, department: str = None, page: int = 1, per_page: int = 5):
        """Get paginated HR list with search"""
        query = {}
        
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}}
            ]
        
        if department:
            query['department'] = department
        
        skip = (page - 1) * per_page
        
        # Get paginated results
        hr_list = list(db.hr.find(query).sort('_id', -1).skip(skip).limit(per_page))
        
        # Count total
        total_count = db.hr.count_documents(query)
        has_next = total_count > page * per_page
        
        # Convert ObjectId to string
        for hr in hr_list:
            hr['_id'] = str(hr['_id'])
        
        # Get analytics data
        analytics = AdminService.get_hr_analytics()
        
        return {
            'hr_list': hr_list,
            'analytics': analytics,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'has_next': has_next
            }
        }
    
    @staticmethod
    def get_hr_analytics():
        """Get HR performance analytics"""
        pipeline = [
            {'$group': {
                '_id': '$hr_id',
                'hired_count': {'$sum': {'$cond': [{'$eq': ['$status', 'Hired']}, 1, 0]}},
                'pending_count': {'$sum': {'$cond': [{'$eq': ['$status', 'Interview Scheduled']}, 1, 0]}}
            }}
        ]
        
        stats_result = list(db.applications.aggregate(pipeline))
        
        hired_data = {}
        pending_data = {}
        
        for item in stats_result:
            hr_id = str(item['_id'])
            hired_data[hr_id] = item['hired_count']
            pending_data[hr_id] = item['pending_count']
        
        return {
            'hired': hired_data,
            'pending': pending_data
        }

admin_service = AdminService()