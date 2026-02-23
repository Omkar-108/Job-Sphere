import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info("Connecting to MongoDB Atlas...")
            
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
            logger.info("✓ MongoDB connection successful")
            
            # Initialize database
            db_name = self._extract_db_name(mongodb_uri) or 'hr_portal'
            self.db = self.client[db_name]
            self._init_collections()
            logger.info(f"Using database: {db_name}")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            
            if "ssl" in str(e).lower() or "tls" in str(e).lower():
                logger.error("SSL/TLS Error: This is a known issue with Python 3.12 + OpenSSL 3.0")
                logger.error("Solution: The app will run in offline mode")
            
            # Fallback to offline mode
            self.client = None
            self.db = None
            self._set_empty_collections()
            logger.warning("Running in offline mode (no database connection)")
    
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
    
    def _set_empty_collections(self):
        """Set empty collections for offline mode"""
        self.users = None
        self.hr = None
        self.admin = None
        self.jobs = None
        self.applications = None
        self.user_activities = None
        self.counters = None
    
    def ensure_indexes(self):
        """Create database indexes for better performance"""
        try:
            if self.db is None:
                logger.warning("Cannot create indexes: No database connection")
                return False
                
            logger.info("Creating database indexes...")
            
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
            
            logger.info("Database indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            return False

    def init_default_data(self):
        """Initialize default data for the application"""
        try:
            if self.db is None:
                logger.warning("Cannot initialize default data: No database connection")
                return False
                
            logger.info("Initializing default data...")
            
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
                logger.info("Default admin user created")
            
            # Initialize counters
            counter_exists = self.db.counters.find_one({"_id": "user_id"})
            if not counter_exists:
                default_counters = [
                    {"_id": "user_id", "seq": 1000},
                    {"_id": "job_id", "seq": 5000},
                    {"_id": "application_id", "seq": 10000},
                    {"_id": "hr_id", "seq": 2000},
                    {"_id": "admin_id", "seq": 100}
                ]
                self.db.counters.insert_many(default_counters)
                logger.info("Default counters created")
            
            logger.info("Default data initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize default data: {str(e)}")
            return False

# Create singleton
db = DatabaseConnection()