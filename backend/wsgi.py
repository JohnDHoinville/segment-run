from dotenv import load_dotenv
import os
import sys
import traceback

# Set up error logging
try:
    print("Starting wsgi.py initialization...")
    
    # Fix path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    
    for path in [current_dir, backend_dir, project_root]:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    print(f"Updated Python path: {sys.path[:5]}")
    
    # Load environment variables from .flaskenv
    try:
        print("Loading environment variables...")
        if os.path.exists('.flaskenv'):
            load_dotenv('.flaskenv')
            print("Loaded .flaskenv successfully")
        else:
            print("No .flaskenv file found, using default environment")
    except Exception as e:
        print(f"Error loading environment variables: {str(e)}")
        traceback.print_exc()
    
    # Import from server.py explicitly instead of app/__init__.py
    print("Importing Flask app from server.py...")
    
    try:
        from server import app
        print("Successfully imported app from server.py")
    except ImportError:
        print("First import attempt failed, trying alternative import paths...")
        try:
            from backend.server import app
            print("Successfully imported app via backend.server")
        except ImportError:
            sys.path.insert(0, os.path.join(current_dir, 'app'))
            print(f"Updated path again: {sys.path[:5]}")
            from server import app
            print("Successfully imported app after path adjustment")
    except Exception as import_error:
        print(f"Error importing app from server.py: {str(import_error)}")
        traceback.print_exc()
        raise
    
    # Log environment info
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Environment variables: PORT={os.environ.get('PORT', 'not set')}, FLASK_ENV={os.environ.get('FLASK_ENV', 'not set')}")
    
except Exception as startup_error:
    print(f"Error during wsgi.py initialization: {str(startup_error)}")
    traceback.print_exc()
    raise

if __name__ == "__main__":
    # Get port from environment variable (default to 5001 if not set)
    port = int(os.environ.get('PORT', 5001))
    
    print(f"Starting Flask server on 0.0.0.0:{port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )