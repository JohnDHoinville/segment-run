#!/usr/bin/env python3
"""
Minimal server to test Heroku deployment.
This only implements a health check endpoint.
"""

import sys
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request

# Create Flask app
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint that doesn't rely on any dependencies."""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'Minimal server is running',
            'timestamp': datetime.now().isoformat(),
            'python_version': sys.version,
            'environment_vars': {k: v for k, v in os.environ.items() if not k.startswith('_')},
            'request_headers': dict(request.headers)
        })
    except Exception as e:
        error_info = {
            'status': 'error',
            'error': str(e),
            'type': type(e).__name__
        }
        return jsonify(error_info), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint that returns a simple message."""
    return jsonify({
        'message': 'Minimal Flask server is running. Try /health for more info.'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 