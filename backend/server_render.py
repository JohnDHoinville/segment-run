#!/usr/bin/env python3
import os
import sys
import traceback
import shutil

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

# Copy static files from backend to root for easier serving
try:
    # Create static directories in project root if they don't exist
    root_static = os.path.join(parent_dir, 'static')
    if not os.path.exists(root_static):
        os.makedirs(root_static)
        print(f"Created root static directory: {root_static}")
    
    root_static_js = os.path.join(root_static, 'js')
    if not os.path.exists(root_static_js):
        os.makedirs(root_static_js)
        print(f"Created root static/js directory: {root_static_js}")
    
    root_static_css = os.path.join(root_static, 'css')
    if not os.path.exists(root_static_css):
        os.makedirs(root_static_css)
        print(f"Created root static/css directory: {root_static_css}")
    
    # Copy JS files
    backend_static_js = os.path.join(backend_dir, 'static', 'js')
    if os.path.exists(backend_static_js):
        for file in os.listdir(backend_static_js):
            if file.endswith('.js'):
                source = os.path.join(backend_static_js, file)
                dest = os.path.join(root_static_js, file)
                shutil.copy2(source, dest)
                print(f"Copied {source} to {dest}")
    
    # Copy CSS files
    backend_static_css = os.path.join(backend_dir, 'static', 'css')
    if os.path.exists(backend_static_css):
        for file in os.listdir(backend_static_css):
            if file.endswith('.css'):
                source = os.path.join(backend_static_css, file)
                dest = os.path.join(root_static_css, file)
                shutil.copy2(source, dest)
                print(f"Copied {source} to {dest}")
    
    # Copy logo files
    backend_static = os.path.join(backend_dir, 'static')
    if os.path.exists(backend_static):
        for file in ['logo192.png', 'logo512.png', 'favicon.ico', 'sw.js']:
            source = os.path.join(backend_static, file)
            if os.path.exists(source):
                dest = os.path.join(root_static, file)
                shutil.copy2(source, dest)
                print(f"Copied {source} to {dest}")
except Exception as e:
    print(f"WARNING: Error copying static files: {e}")
    traceback.print_exc()

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