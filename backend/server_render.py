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
    # Import the Flask app
    print("Importing Flask app...")
    from app import app
    
    # Force production mode settings
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Simple test route
    @app.route('/server-test')
    def server_test():
        return {'status': 'ok', 'message': 'Server is running properly'}
    
    # Root route is already defined in app/__init__.py
    
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 10000))
        print(f"Starting Flask server on 0.0.0.0:{port} in PRODUCTION mode")
        # Explicitly set all production flags
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=False, 
            use_reloader=False, 
            threaded=True
        )
except Exception as e:
    print(f"ERROR DURING SERVER STARTUP: {str(e)}")
    traceback.print_exc()
    sys.exit(1) 