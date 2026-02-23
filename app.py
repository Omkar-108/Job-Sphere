# app.py
from flask import Flask, render_template
from flask_sock import Sock
import os
import json
import logging
import threading
import time
import sys
import subprocess
import atexit
import requests
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO to reduce verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific loggers to higher levels to suppress verbose output
logging.getLogger('pymongo').setLevel(logging.WARNING)
logging.getLogger('pymongo.topology').setLevel(logging.WARNING)
logging.getLogger('pymongo.connection').setLevel(logging.WARNING)

# Keep your application logger at DEBUG level if needed for debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Import database with error handling
try:
    from database.setup import db
    logger.info("Database module imported successfully")
except ImportError as e:
    logger.error(f"Failed to import database module: {e}")
    db = None

# Agent Server Manager Class
class AgentServerManager:
    def __init__(self):
        self.process = None
        self.agent_server_url = "http://localhost:8000"  # Default URL for FastAPI agent server
        
    def start(self):
        """Start the agent server"""
        print("Starting Agent Server...")
        
        try:
            # Check if already running
            try:
                response = requests.get(f"{self.agent_server_url}/health", timeout=2)
                if response.status_code == 200:
                    print(f"Agent Server already running at {self.agent_server_url}")
                    return True
            except:
                pass
            
            # Path to agent server script
            agent_server_path = os.path.join(
                os.path.dirname(__file__), 
                'services', 
                'agent_api_server.py'
            )
            
            if not os.path.exists(agent_server_path):
                # Try alternative path
                agent_server_path = os.path.join(
                    os.path.dirname(__file__), 
                    'agent_api_server.py'
                )
            
            if os.path.exists(agent_server_path):
                # Start agent server with Python
                self.process = subprocess.Popen(
                    [sys.executable, agent_server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(__file__)
                )
            else:
                print("Agent server file not found. Starting minimal server...")
                # Start a minimal agent server
                self._start_minimal_server()
            
            # Wait for server to start
            for i in range(15):
                try:
                    response = requests.get(f"{self.agent_server_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"Agent Server started at {self.agent_server_url}")
                        # Set environment variable
                        os.environ['AGENT_SERVER_URL'] = self.agent_server_url
                        return True
                except:
                    time.sleep(1)
            
            print("Agent Server failed to start")
            return False
            
        except Exception as e:
            print(f"Error starting Agent Server: {e}")
            return False
    
    def _start_minimal_server(self):
        """Start a minimal Flask agent server if main one isn't available"""
        import threading
        
        def run_minimal_server():
            from flask import Flask, request, jsonify
            import threading as th
            
            app = Flask(__name__)
            
            @app.route('/health')
            def health():
                return jsonify({"status": "healthy", "type": "minimal"})
            
            @app.route('/api/chat', methods=['POST'])
            def chat():
                data = request.json
                message = data.get('message', '')
                user_id = data.get('user_id', 'anonymous')
                
                response_text = f"Minimal Agent Server processed: {message[:100]}..."
                
                return jsonify({
                    "response": response_text,
                    "source": "minimal_agent_server",
                    "user_id": user_id
                })
            
            app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
        
        # Start in a thread
        thread = threading.Thread(target=run_minimal_server, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop agent server"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            print("Agent Server stopped")

# Initialize agent server manager
agent_manager = AgentServerManager()

# Function to start agent server in background
def start_agent_server_background():
    """Start agent server in background thread"""
    import time
    time.sleep(2)  # Give main app time to initialize logging
    
    print("\n" + "="*50)
    print("Initializing Agent Server...")
    print("="*50)
    
    if agent_manager.start():
        print(f"\nAGENT_SERVER_URL set to: {os.environ.get('AGENT_SERVER_URL')}")
        print("Agent Server is ready")
    else:
        print("Agent Server not available. Chatbot will use fallback providers.")
        # Set a fallback URL
        os.environ['AGENT_SERVER_URL'] = "http://localhost:8000"
    
    print("="*50 + "\n")

# Start agent server in background thread
agent_thread = threading.Thread(target=start_agent_server_background, daemon=True)
agent_thread.start()

# Register cleanup
atexit.register(agent_manager.stop)

# Import routes with error handling
routes_modules = [
    ('main_routes', 'main_bp'),
    ('auth_routes', 'auth_bp'),
    ('user_routes', 'user_bp'),
    ('hr_routes', 'hr_bp'),
    ('admin_routes', 'admin_bp'),
    ('video_routes', 'video_bp'),
    ('manual_verification_routes', 'manual_verification_bp'),
    ('chatbot_routes', 'chatbot_bp'),
    ('scheduler_routes', 'scheduler_bp')
]

blueprints = []
for module_name, bp_name in routes_modules:
    try:
        module = __import__(f'routes.{module_name}', fromlist=[bp_name])
        blueprint = getattr(module, bp_name)
        blueprints.append(blueprint)
        logger.info(f"Successfully imported {module_name}")
    except ImportError as e:
        logger.error(f"Failed to import {module_name}: {e}")

# Initialize Flask app
# First try the parent directory (where static and templates folders are actually located)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# If templates not found in parent, try current directory
if not os.path.isdir(TEMPLATES_DIR):
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')

# If still not found, try the actual project root
if not os.path.isdir(TEMPLATES_DIR):
    # Go up two levels from backend/ to project root
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"TEMPLATES_DIR: {TEMPLATES_DIR}")
logger.info(f"STATIC_DIR: {STATIC_DIR}")
logger.info(f"Templates exists: {os.path.isdir(TEMPLATES_DIR)}")
logger.info(f"Static exists: {os.path.isdir(STATIC_DIR)}")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
app.config['UPLOAD_FOLDER'] = os.path.join(STATIC_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize WebSocket
sock = Sock(app)

# Register blueprints
for blueprint in blueprints:
    try:
        app.register_blueprint(blueprint)
        logger.info(f"Registered blueprint: {blueprint.name}")
    except Exception as e:
        logger.error(f"Failed to register blueprint {blueprint.name}: {e}")

# Application route (needs access to upload folder)
try:
    from services.application_service import ApplicationService
    from services.file_service import FileService
    logger.info("Application services imported successfully")
except ImportError as e:
    logger.error(f"Failed to import application services: {e}")
    ApplicationService = None
    FileService = None

@app.route('/api/apply', methods=['POST'])
@app.route('/apply', methods=['POST'])
def apply_job():
    """Handle job application with file upload"""
    from flask import request, jsonify, session
    
    if ApplicationService is None:
        return jsonify({'error': 'Application service not available'}), 500
    
    try:
        app_service = ApplicationService(app.config['UPLOAD_FOLDER'])
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Please login to apply'}), 401
        
        result = app_service.apply_for_job(request.form, request.files, user_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in apply_job: {e}")
        return jsonify({'error': 'An error occurred while processing your application'}), 500

# File routes
@app.route('/resume/<path:filename>')
def view_resume(filename):
    """View resume file"""
    if FileService is None:
        from flask import abort
        abort(404)
    
    try:
        file_service = FileService(app.config['UPLOAD_FOLDER'])
        result = file_service.view_resume(filename)
        if not result:
            from flask import abort
            abort(404)
        return result
    except Exception as e:
        logger.error(f"Error viewing resume: {e}")
        from flask import abort
        abort(404)

@app.route('/resume/download/<path:filename>')
def download_resume(filename):
    """Download resume file"""
    if FileService is None:
        from flask import abort
        abort(404)
    
    try:
        file_service = FileService(app.config['UPLOAD_FOLDER'])
        result = file_service.download_resume(filename)
        if not result:
            from flask import abort
            abort(404)
        return result
    except Exception as e:
        logger.error(f"Error downloading resume: {e}")
        from flask import abort
        abort(404)

# ============== WEB SOCKET ROUTES (must be in app.py) ==============
@app.route('/ws/hr/<app_id>')
def ws_hr_route(app_id):
    """HR WebSocket route - redirects to WebSocket handler"""
    from flask import redirect, url_for
    return redirect(url_for('ws_hr', app_id=app_id))

@app.route('/ws/user/<app_id>')
def ws_user_route(app_id):
    """User WebSocket route - redirects to WebSocket handler"""
    from flask import redirect, url_for
    return redirect(url_for('ws_user', app_id=app_id))

@sock.route('/ws/hr/<app_id>')
def ws_hr(ws, app_id):
    """HR WebSocket handler - delegates to video service"""
    try:
        from services.video_service import video_service
        video_service.handle_hr_connection(ws, app_id)
    except Exception as e:
        logger.error(f"Error in HR WebSocket connection: {e}")

@sock.route('/ws/user/<app_id>')
def ws_user(ws, app_id):
    """User WebSocket handler - delegates to video service"""
    try:
        from services.video_service import video_service
        video_service.handle_user_connection(ws, app_id)
    except Exception as e:
        logger.error(f"Error in user WebSocket connection: {e}")
# ================================================================

# Favicon and error handlers
@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route('/test-interface')
def test_interface():
    """Test interface for development"""
    return render_template('test_interface.html')

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return render_template('500.html'), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    from flask import jsonify
    import requests
    
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'database': 'connected' if db and db.client else 'disconnected',
        'fastapi_agent': 'unknown',
        'agent_server': 'unknown'
    }
    
    # Check if FastAPI agent server is running
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=2)
        if response.status_code == 200:
            status['fastapi_agent'] = 'connected'
        else:
            status['fastapi_agent'] = 'error'
    except Exception:
        status['fastapi_agent'] = 'disconnected'
    
    # Check if Agent Server is running
    try:
        agent_server_url = os.environ.get('AGENT_SERVER_URL', 'http://localhost:8000')
        response = requests.get(f"{agent_server_url}/health", timeout=2)
        if response.status_code == 200:
            status['agent_server'] = 'connected'
        else:
            status['agent_server'] = 'error'
    except Exception:
        status['agent_server'] = 'disconnected'
    
    return jsonify(status)

# Context processor to make variables available in templates
@app.context_processor
def inject_variables():
    """Inject variables into all templates"""
    return {
        'app_name': 'Job Sphere',
        'current_year': time.strftime('%Y')
    }

# Template filters
@app.template_filter('datetime')
def datetime_filter(value):
    """Format datetime values"""
    if isinstance(value, str):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y at %I:%M %p')
        except:
            return value
    return value

@app.template_filter('currency')
def currency_filter(value):
    """Format currency values"""
    try:
        return f"${float(value):,.2f}"
    except:
        return value

def initialize_database():
    """Initialize database with indexes and default data"""
    if db is None:
        logger.warning("Database not available - skipping initialization")
        return
    
    try:
        # Ensure indexes
        db.ensure_indexes()
        logger.info("Database indexes ensured")
        
        # Initialize default data
        db.init_default_data()
        logger.info("Default data initialized")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

def start_background_tasks():
    """Start background tasks"""
    def background_task():
        """Background task for periodic operations"""
        while True:
            try:
                # Add periodic tasks here
                time.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in background task: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    # Start background thread
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    logger.info("Background tasks started")

def start_all_services():
    """Start all required services"""
    print("\n" + "="*50)
    print("Starting Job Sphere Application")
    print("="*50)
    
    # Agent server is started in background thread above
    
    # Initialize database
    initialize_database()
    
    # Start background tasks
    start_background_tasks()
    
    print("\nAll services initialized")
    print("="*50 + "\n")

if __name__ == '__main__':
    logger.info("Starting Job Sphere application...")
    
    # Call this function when starting
    start_all_services()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port} with debug={debug}")
    
    # Start app
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        threaded=True
    )