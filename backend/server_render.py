#!/usr/bin/env python3
import os
import sys
import traceback

# Print startup diagnostics
print("=" * 50)
print("RENDER SERVER STARTING")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
print(f"Environment: {os.environ.get('FLASK_ENV', 'not set')}")
print(f"PORT: {os.environ.get('PORT', 'not set')}")
print(f"RENDER SERVICE: {os.environ.get('RENDER_SERVICE_NAME', 'not set')}")
print(f"RENDER EXTERNAL URL: {os.environ.get('RENDER_EXTERNAL_URL', 'not set')}")
print(f"RENDER INTERNAL URL: {os.environ.get('RENDER_INTERNAL_URL', 'not set')}")
print("=" * 50)

# Make sure backend directory is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Also add parent directory to path
parent_dir = os.path.dirname(backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

print(f"Python path: {sys.path}")

try:
    # Import the server module instead of app directly
    print("Importing server module...")
    import server
    
    # Get the app from server
    app = server.app
    
    # Force production mode settings
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Root route and static file handling is already defined in server.py
    # DO NOT add additional routes here that would override server.py routes
    
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 10000))
        print(f"Starting Flask server on 0.0.0.0:{port} in PRODUCTION mode")
        # Explicitly set all production flags
        app.run(
            host='0.0.0.0', 
            port=port,
            debug=False,
            use_reloader=False  # Disable reloader in production
        )
except Exception as e:
    print(f"ERROR DURING SERVER STARTUP: {str(e)} ({e.__class__.__name__}, line {e.__traceback__.tb_lineno if e.__traceback__ else 'unknown'})")
    traceback.print_exc() 