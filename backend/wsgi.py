from dotenv import load_dotenv
import os
import sys
import traceback

# Set up error logging
try:
    print("Starting wsgi.py initialization...")
    
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
    
    # Change relative import to absolute import 
    print("Importing Flask app...")
    
    # Add the current directory to the path to make imports work
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    
    try:
        from app import app
        print("Successfully imported app")
    except Exception as import_error:
        print(f"Error importing app: {str(import_error)}")
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