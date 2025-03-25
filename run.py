#!/usr/bin/env python3
"""
Simple script to run the backend server.
Usage: python run.py
"""
import os
import sys
import subprocess

def run_backend():
    """Run the Flask backend server"""
    print("Starting Flask backend server...")
    
    # Change to the backend directory
    os.chdir('backend')
    
    # Add the current directory to PYTHONPATH to resolve imports
    env = os.environ.copy()
    
    # Use the absolute path for more reliable Python module resolution
    backend_path = os.path.abspath('.')
    env['PYTHONPATH'] = backend_path
    
    print(f"Using PYTHONPATH: {env['PYTHONPATH']}")
    
    try:
        # Run the app with proper Python path set
        subprocess.run(
            [sys.executable, 'app.py'], 
            env=env, 
            check=True
        )
    except KeyboardInterrupt:
        print("\nBackend server stopped")
    except subprocess.CalledProcessError as e:
        print(f"\nError starting backend: {e}")
        print("\nTry running the server directly with:")
        print("cd backend && python app.py")
        raise
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        raise

if __name__ == "__main__":
    run_backend() 