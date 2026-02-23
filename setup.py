import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import datetime

load_dotenv()

class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self):
        """Initialize MongoDB connection with SSL/TLS compatibility fix"""
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        
        try:
            # Create connection with SSL compatibility fix
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                retryWrites=False  # Disable retry writes for SSL compatibility
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Initialize database
            db_name = self._extract_db_name(mongodb_uri) or 'hr_portal'
            self.db = self.client[db_name]
            self._init_collections()
            
        except Exception as e:
            
            if "ssl" in str(e).lower() or "tls" in str(e).lower():
                pass
            
            # Fallback to offline mode
            self.client = None
            self.db = None
            self._set_empty_collections()
    
    def _extract_db_name(self, uri):
        """Extract database name from MongoDB URI"""
        try:
            if '/' in uri:
                db_part = uri.split('/')[-1]
                if '?' in db_part:
                    db_part = db_part.split('?')[0]
                if db_part:
                    return db_part
        except:
            pass
        return None
    
    def _init_collections(self):
        """Initialize collection references"""
        self.users = self.db.users
        self.hr = self.db.hr
        self.admin = self.db.admin
        self.jobs = self.db.jobs
        self.applications = self.db.applications
        self.user_activities = self.db.user_activities
        self.counters = self.db.counters
        # Add collections for test_service, offer_service
        self.tests = self.db.tests
        self.questions = self.db.questions
        self.test_submissions = self.db.test_submissions
        self.job_offers = self.db.job_offers
        self.interviews = self.db.interviews
        self.interview_feedback = self.db.interview_feedback
        self.candidate_pipeline = self.db.candidate_pipeline
        self.email_templates = self.db.email_templates
        self.email_logs = self.db.email_logs
        # Add schedule_events collection for workflow_service
        self.schedule_events = self.db.schedule_events
    
    def _set_empty_collections(self):
        """Set empty collections for offline mode"""
        self.users = None
        self.hr = None
        self.admin = None
        self.jobs = None
        self.applications = None
        self.user_activities = None
        self.counters = None
        # Add collections for test_service, offer_service
        self.tests = None
        self.questions = None
        self.test_submissions = None
        self.job_offers = None
        self.interviews = None
        self.interview_feedback = None
        self.candidate_pipeline = None
        self.email_templates = None
        self.email_logs = None
        # Add schedule_events collection for workflow_service
        self.schedule_events = None
    
    def ensure_indexes(self):
        """Create database indexes for better performance"""
        try:
            if self.db is None:
                return False
            
            # Users collection indexes
            self.db.users.create_index("email", unique=True)
            self.db.users.create_index("user_id")
            
            # HR collection indexes
            self.db.hr.create_index("hr_id", unique=True)
            self.db.hr.create_index("email", unique=True)
            
            # Admin collection indexes
            self.db.admin.create_index("admin_id", unique=True)
            self.db.admin.create_index("email", unique=True)
            
            # Jobs collection indexes
            self.db.jobs.create_index("job_id")
            self.db.jobs.create_index("posted_by")
            self.db.jobs.create_index("status")
            
            # Applications collection indexes
            self.db.applications.create_index("application_id", unique=True)
            self.db.applications.create_index("job_id")
            self.db.applications.create_index("user_id")
            
            # Counters collection indexes
            self.db.counters.create_index("_id", unique=True)
            
            # Tests collection indexes
            self.db.tests.create_index("job_id")
            self.db.tests.create_index("status")
            self.db.tests.create_index("created_at")
            
            # Questions collection indexes
            self.db.questions.create_index("test_id")
            self.db.questions.create_index("category")
            
            # Test submissions collection indexes
            self.db.test_submissions.create_index("test_id")
            self.db.test_submissions.create_index("candidate_id")
            self.db.test_submissions.create_index("application_id")
            self.db.test_submissions.create_index("status")
            
            # Job offers collection indexes
            self.db.job_offers.create_index("application_id")
            self.db.job_offers.create_index("job_id")
            self.db.job_offers.create_index("candidate_id")
            self.db.job_offers.create_index("status")
            self.db.job_offers.create_index("created_at")
            
            # Interviews collection indexes
            self.db.interviews.create_index("application_id")
            self.db.interviews.create_index("job_id")
            self.db.interviews.create_index("candidate_id")
            self.db.interviews.create_index("hr_id")
            self.db.interviews.create_index("status")
            self.db.interviews.create_index("scheduled_datetime")
            
            # Interview feedback collection indexes
            self.db.interview_feedback.create_index("interview_id")
            self.db.interview_feedback.create_index("interviewer_id")
            
            # Candidate pipeline collection indexes
            self.db.candidate_pipeline.create_index("application_id")
            self.db.candidate_pipeline.create_index("current_stage")
            self.db.candidate_pipeline.create_index("priority")
            
            # Email templates collection indexes
            self.db.email_templates.create_index("template_type")
            self.db.email_templates.create_index("name")
            
            # Email logs collection indexes
            self.db.email_logs.create_index("recipient_email")
            self.db.email_logs.create_index("sent_at")
            self.db.email_logs.create_index("status")
            
            # Schedule events collection indexes
            self.db.schedule_events.create_index("event_type")
            self.db.schedule_events.create_index("scheduled_datetime")
            self.db.schedule_events.create_index("participants")
            self.db.schedule_events.create_index("status")
            
            return True
            
        except Exception as e:
            return False

    def init_default_data(self):
        """Initialize default data for the application"""
        try:
            if self.db is None:
                return False
            
            # Check if admin user exists
            admin_exists = self.db.admin.find_one({"role": "admin"})
            if not admin_exists:
                # Create default admin user
                admin_user = {
                    "admin_id": "admin_001",
                    "email": "admin@jobsphere.com",
                    "password": "admin123",  # In production, this should be hashed
                    "name": "System Administrator",
                    "role": "admin",
                    "created_at": datetime.utcnow(),
                    "is_active": True
                }
                self.db.admin.insert_one(admin_user)
            
            # Initialize counters
            counter_exists = self.db.counters.find_one({"_id": "user_id"})
            if not counter_exists:
                default_counters = [
                    {"_id": "user_id", "seq": 1000},
                    {"_id": "job_id", "seq": 5000},
                    {"_id": "application_id", "seq": 10000},
                    {"_id": "hr_id", "seq": 2000},
                    {"_id": "admin_id", "seq": 100},
                    {"_id": "test_id", "seq": 3000},
                    {"_id": "question_id", "seq": 30000},
                    {"_id": "test_submission_id", "seq": 40000},
                    {"_id": "offer_id", "seq": 50000},
                    {"_id": "interview_id", "seq": 60000}
                ]
                self.db.counters.insert_many(default_counters)
            
            return True
            
        except Exception as e:
            return False

# Create singleton
db = DatabaseConnection()