#!/usr/bin/env python3
"""
Multi-server startup script for Job Sphere
Runs both Flask (main app) and FastAPI (agent API) servers
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class ServerManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_flask_server(self):
        """Start the Flask main application"""
        try:
            print("Starting Flask server on port 5000...")
            flask_process = subprocess.Popen([
                sys.executable, "app.py"
            ], cwd=Path(__file__).parent)
            self.processes['flask'] = flask_process
            print("Flask server started")
        except Exception as e:
            print(f"Failed to start Flask server: {e}")
            
    def start_fastapi_server(self):
        """Start the FastAPI agent server"""
        try:
            print("Starting FastAPI agent server on port 8000...")
            fastapi_process = subprocess.Popen([
                sys.executable, "agent_api_server.py"
            ], cwd=Path(__file__).parent)
            self.processes['fastapi'] = fastapi_process
            print("FastAPI agent server started")
        except Exception as e:
            print(f"Failed to start FastAPI server: {e}")
    
    def monitor_servers(self):
        """Monitor server processes and restart if needed"""
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            for name, process in self.processes.items():
                if process.poll() is not None:  # Process has terminated
                    print(f"{name.capitalize()} server has stopped (exit code: {process.returncode})")
                    
                    if self.running:  # Only restart if we're supposed to be running
                        print(f"Restarting {name.capitalize()} server...")
                        if name == 'flask':
                            threading.Thread(target=self.start_flask_server, daemon=True).start()
                        elif name == 'fastapi':
                            threading.Thread(target=self.start_fastapi_server, daemon=True).start()
    
    def shutdown(self):
        """Gracefully shutdown all servers"""
        print("\nShutting down servers...")
        self.running = False
        
        for name, process in self.processes.items():
            try:
                print(f"Stopping {name.capitalize()} server...")
                process.terminate()
                process.wait(timeout=5)
                print(f"{name.capitalize()} server stopped")
            except subprocess.TimeoutExpired:
                print(f" Force killing {name.capitalize()} server...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"Error stopping {name.capitalize()} server: {e}")
    
    def start(self):
        """Start all servers and monitor them"""
        print(" Job Sphere Multi-Server Startup")
        print("=" * 50)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start servers
        self.start_flask_server()
        time.sleep(2)  # Give Flask time to start
        
        self.start_fastapi_server()
        time.sleep(2)  # Give FastAPI time to start
        
        print("\n All servers started successfully!")
        print("Flask server: http://localhost:5000")
        print("FastAPI agent server: http://localhost:8000")
        print("FastAPI docs: http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all servers")
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=self.monitor_servers, daemon=True)
        monitor_thread.start()
        
        try:
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    # Check Python modules
    required_modules = ['flask', 'fastapi', 'uvicorn']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"{module}")
        except ImportError:
            missing_modules.append(module)
            print(f"{module} - NOT FOUND")
    
    if missing_modules:
        print(f"\nMissing dependencies: {', '.join(missing_modules)}")
        print("Please install them using: pip install " + " ".join(missing_modules))
        return False
    
    print("All dependencies found!")
    return True

def main():
    """Main entry point"""
    if not check_dependencies():
        sys.exit(1)
    
    manager = ServerManager()
    manager.start()

if __name__ == "__main__":
    main()