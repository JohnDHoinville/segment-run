#!/usr/bin/env python3
"""
Quick script to check Python syntax in a file.
This will help find syntax errors before deployment.
"""

import os
import sys
import py_compile
import traceback

def check_syntax(filename):
    """Check if a Python file has correct syntax."""
    print(f"Checking syntax of {filename}...")
    
    # First, check if the file exists
    if not os.path.exists(filename):
        print(f"ERROR: File {filename} does not exist.")
        return False
    
    # Try to compile the file to check for syntax errors
    try:
        py_compile.compile(filename, doraise=True)
        print(f"✓ {filename} has valid Python syntax.")
        return True
    except Exception as e:
        print(f"✗ Syntax error in {filename}:")
        print(f"  Error: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Default to server.py if no file provided
    filename = "server.py"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    success = check_syntax(filename)
    if not success:
        sys.exit(1) 