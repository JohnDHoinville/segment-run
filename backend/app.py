#!/usr/bin/env python3
"""
Main entry point for the Flask application.
"""
import sys
import os

# Ensure the current directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the Flask app instance
from server import app

if __name__ == '__main__':
    print("Starting server on http://localhost:5001")
    app.run(
        debug=True,
        host='localhost',
        port=5001
    ) 