# database/repository.py
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .models import User, HR, Job, Application, UserActivity
from .setup import db
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    def find_by_email_or_username(identifier: str) -> Optional[User]:
        logger.info(f"[DEBUG] UserRepository.find_by_email_or_username called with: {identifier}")
        if db.client is None:
            logger.warning("Database connection not available - user lookup failed")
            return None
        user_data = db.users.find_one({
            '$or': [
                {'email': identifier},
                {'username': identifier}
            ]
        })
        logger.info(f"[DEBUG] User data found: {user_data is not None}")
        if user_data:
            logger.info(f"[DEBUG] User email: {user_data.get('email')}, username: {user_data.get('username')}")
        return User.from_dict(user_data) if user_data else None

    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        logger.info(f"[DEBUG] UserRepository.find_by_email called with: {email}")
        if db.client is None:
            logger.warning("Database connection not available - user lookup failed")
            return None
        user_data = db.users.find_one({'email': email})
        logger.info(f"[DEBUG] User data found by email: {user_data is not None}")
        return User.from_dict(user_data) if user_data else None
    
    @staticmethod
    def find_by_username(username: str) -> Optional[User]:
        if db.client is None:
            logger.warning("Database connection not available - user lookup failed")
            return None
        user_data = db.users.find_one({'username': username})
        return User.from_dict(user_data) if user_data else None
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[User]:
        if db.client is None:
            logger.warning("Database connection not available - user lookup failed")
            return None
        # Try both _id and user_id fields for compatibility
        user_data = db.users.find_one({'_id': user_id})
        if not user_data:
            user_data = db.users.find_one({'user_id': user_id})
        return User.from_dict(user_data) if user_data else None
    
    @staticmethod
    def create(user: User) -> str:
        if db.client is None:
            logger.error("Database connection not available - cannot create user")
            raise Exception("Database connection not available")
        user_dict = user.to_dict(include_id=False)
        if "_id" in user_dict and user_dict["_id"] is None:
            del user_dict["_id"]
        if user_dict.get("user_id") is None:
        # Option A: Assign a unique string (like a UUID)
            import uuid
        user_dict["user_id"] = str(uuid.uuid4())
        result = db.users.insert_one(user_dict)
        return str(result.inserted_id)
    
    @staticmethod
    def update(user_id: str, update_data: Dict[str, Any]) -> bool:
        if db.client is None:
            logger.warning("Database connection not available - user update failed")
            return False
        result = db.users.update_one(
            {'user_id': user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(user_id: str) -> bool:
        if db.client is None:
            logger.warning("Database connection not available - user deletion failed")
            return False
        result = db.users.delete_one({'user_id': user_id})
        return result.deleted_count > 0
    
    @staticmethod
    def find_all(limit: int = None) -> List[User]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch users")
            return []
        cursor = db.users.find()
        if limit:
            cursor = cursor.limit(limit)
        return [User.from_dict(user_data) for user_data in cursor]

class HRRepository:
    @staticmethod
    def find_by_email_or_username(identifier: str) -> Optional[HR]:
        """Find HR by email or username"""
        logger.info(f"[DEBUG] HRRepository.find_by_email_or_username called with: {identifier}")
        if db.client is None:
            logger.warning("Database connection not available - HR lookup failed")
            return None
        
        # Try email first, then username
        hr_data = db.hr.find_one({'email': identifier})
        logger.info(f"[DEBUG] HR data found by email: {hr_data is not None}")
        if not hr_data:
            hr_data = db.hr.find_one({'username': identifier})
            logger.info(f"[DEBUG] HR data found by username: {hr_data is not None}")
        
        return HR.from_dict(hr_data) if hr_data else None
    
    @staticmethod
    def find_by_email(email: str) -> Optional[HR]:
        if db.client is None:
            logger.warning("Database connection not available - HR lookup failed")
            return None
        hr_data = db.hr.find_one({'email': email})
        return HR.from_dict(hr_data) if hr_data else None
    
    @staticmethod
    def find_by_username(username: str) -> Optional[HR]:
        if db.client is None:
            logger.warning("Database connection not available - HR lookup failed")
            return None
        hr_data = db.hr.find_one({'username': username})
        return HR.from_dict(hr_data) if hr_data else None
    
    @staticmethod
    def find_by_id(hr_id: str) -> Optional[HR]:
        if db.client is None:
            logger.warning("Database connection not available - HR lookup failed")
            return None
        # Try both _id and hr_id fields for compatibility
        hr_data = db.hr.find_one({'_id': hr_id})
        if not hr_data:
            hr_data = db.hr.find_one({'hr_id': hr_id})
        return HR.from_dict(hr_data) if hr_data else None
    
    @staticmethod
    def create(hr: HR) -> str:
        if db.client is None:
            logger.error("Database connection not available - cannot create HR")
            raise Exception("Database connection not available")
        hr_dict = hr.to_dict(include_id=False)
        if "_id" in hr_dict and hr_dict["_id"] is None:
            del hr_dict["_id"]
        result = db.hr.insert_one(hr_dict)
        return str(result.inserted_id)
    
    @staticmethod
    def find_all() -> List[HR]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch HR users")
            return []
        return [HR.from_dict(hr_data) for hr_data in db.hr.find()]

class JobRepository:
    @staticmethod
    def create(job: Job) -> str:
        if db.client is None:
            logger.error("Database connection not available - cannot create job")
            raise Exception("Database connection not available")
        job_dict = job.to_dict(include_id=False)
        if "_id" in job_dict and job_dict["_id"] is None:
            del job_dict["_id"]
        result = db.jobs.insert_one(job_dict)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(job_id: str) -> Optional[Job]:
        if db.client is None:
            logger.warning("Database connection not available - job lookup failed")
            return None
        try:
            job_data = db.jobs.find_one({'_id': ObjectId(job_id)})
            return Job.from_dict(job_data) if job_data else None
        except:
            # Try with string ID
            job_data = db.jobs.find_one({'job_id': job_id})
            return Job.from_dict(job_data) if job_data else None
    
    @staticmethod
    def get_all_active(active_only: bool = True) -> List[Job]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch jobs")
            return []
        now = datetime.now(timezone.utc) 

        # 1. Maintenance: Update jobs that just passed their endDate
        # This ensures the 'find' query below returns the correct current status
        db.jobs.update_many(
            {"hiring_end": {"$lt": now}, "status": "Active"},
            {"$set": {"status": "Not Active"}}
        )

        # 2. Automation: Ensure 3-month deletion logic is active
        # (Safe to run every time; MongoDB only creates it once)
        # 7,776,000 seconds = approx. 90 days
        db.jobs.create_index("hiring_end", expireAfterSeconds=7776000)
        query = {}
        if active_only:
            query['status'] = 'ctive'
        return [Job.from_dict(job_data) for job_data in db.jobs.find(query)]
    
    @staticmethod
    def find_by_hr(hr_id: str) -> List[Job]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch HR jobs")
            return []
        return [Job.from_dict(job_data) for job_data in db.jobs.find({'hr_id': hr_id})]
    
    @staticmethod
    def update(job_id: str, update_data: Dict[str, Any]) -> bool:
        if db.client is None:
            logger.warning("Database connection not available - job update failed")
            return False
        try:
            result = db.jobs.update_one(
                {'_id': ObjectId(job_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            # Try with string ID
            result = db.jobs.update_one(
                {'job_id': job_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
    
    @staticmethod
    def delete(job_id: str) -> bool:
        if db.client is None:
            logger.warning("Database connection not available - job deletion failed")
            return False
        try:
            result = db.jobs.delete_one({'_id': ObjectId(job_id)})
            return result.deleted_count > 0
        except:
            # Try with string ID
            result = db.jobs.delete_one({'job_id': job_id})
            return result.deleted_count > 0
       
    @staticmethod
    def get_all_jobs() -> List[Job]:
        """
        Updates expired job statuses, ensures TTL cleanup,
        and returns every job in the collection.
        """
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch jobs")
            return []

        now = datetime.now(timezone.utc)

        # 1. Update statuses so the returned data is accurate
        db.jobs.update_many(
            {"endDate": {"$lt": now}, "status": "active"},
            {"$set": {"status": "not active"}}
        )

        # 2. Ensure the 3-month auto-delete index is active
        db.jobs.create_index("endDate", expireAfterSeconds=7776000)

        # 3. Fetch everything (empty query {})
        return [Job.from_dict(job_data) for job_data in db.jobs.find({})]


class ApplicationRepository:
    @staticmethod
    def create(application: Application) -> str:
        if db.client is None:
            logger.error("Database connection not available - cannot create application")
            raise Exception("Database connection not available")
        app_dict = application.to_dict(include_id=False)
        if "_id" in app_dict and app_dict["_id"] is None:
            del app_dict["_id"]
        result = db.applications.insert_one(app_dict)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_job(job_id: str) -> List[Application]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch job applications")
            return []
        try:
            applications = db.applications.find({'job_id': ObjectId(job_id)})
        except:
            applications = db.applications.find({'job_id': job_id})
        return [Application.from_dict(app_data) for app_data in applications]
    
    @staticmethod
    def find_by_applicant(email: str) -> List[Application]:
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch applicant applications")
            return []
        return [Application.from_dict(app_data) for app_data in db.applications.find({'email': email})]
    
    @staticmethod
    def update_status(application_id: str, status: str) -> bool:
        if db.client is None:
            logger.warning("Database connection not available - application status update failed")
            return False
        try:
            result = db.applications.update_one(
                {'_id': ObjectId(application_id)},
                {"$set": {'status': status, 'updated_at': datetime.now()}}
            )
            return result.modified_count > 0
        except:
            result = db.applications.update_one(
                {'application_id': application_id},
                {"$set": {'status': status, 'updated_at': datetime.now()}}
            )
            return result.modified_count > 0
    
    @staticmethod
    def get_user_applications(user_id: str) -> List[Application]:
        """Get all applications for a specific user by user_id"""
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch user applications")
            return []
        applications = db.applications.find({'user_id': user_id})
        return [Application.from_dict(app_data) for app_data in applications]
    @staticmethod
    def get_applications_for_hr_id(hr_id: str) -> List[Application]:
        """Get all applications for a specific HR by hr_id"""
        if db.client is None:
            logger.warning("Database connection not available - cannot fetch HR applications")
            return []
        applications = db.applications.find({'hr_id': hr_id})
        return [Application.from_dict(app_data) for app_data in applications]


class DatabaseRepository:
    """Generic database repository for common operations"""
    
    def __init__(self):
        self.db = db
    
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a single document"""
        if self.db.client is None:
            logger.error(f"Database connection not available - cannot insert into {collection}")
            raise Exception("Database connection not available")
        # Get the actual collection from the database
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            raise Exception(f"Collection {collection} not available")
        result = collection_obj.insert_one(document)
        return str(result.inserted_id)
    
    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot find in {collection}")
            return None
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return None
        return collection_obj.find_one(query)
    
    def find_many(self, collection: str, query: Dict[str, Any],
                  sort: List[tuple] = None) -> Any:
        """Find multiple documents"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot find in {collection}")
            return []
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return []
        cursor = collection_obj.find(query)
        if sort:
            cursor = cursor.sort(sort)
        return cursor
    
    def update_one(self, collection: str, query: Dict[str, Any],
                   update: Dict[str, Any]) -> bool:
        """Update a single document"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot update in {collection}")
            return False
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return False
        result = collection_obj.update_one(query, {"$set": update})
        return result.modified_count > 0
    
    def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        """Delete a single document"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot delete from {collection}")
            return False
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return False
        result = collection_obj.delete_one(query)
        return result.deleted_count > 0
    
    def delete_many(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot delete from {collection}")
            return 0
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return 0
        result = collection_obj.delete_many(query)
        return result.deleted_count
    
    def count(self, collection: str, query: Dict[str, Any] = None) -> int:
        """Count documents"""
        if self.db.client is None:
            logger.warning(f"Database connection not available - cannot count in {collection}")
            return 0
        collection_obj = getattr(self.db, collection, None)
        if collection_obj is None:
            logger.error(f"Collection {collection} not available")
            return 0
        if query is None:
            query = {}
        return collection_obj.count_documents(query)

# Repository instances for easy import
user_repo = UserRepository()
hr_repo = HRRepository()
job_repo = JobRepository()
app_repo = ApplicationRepository()