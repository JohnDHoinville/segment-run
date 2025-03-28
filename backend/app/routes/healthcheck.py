from flask import Blueprint, jsonify
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint that Render can use to verify the app is running."""
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'environment': os.environ.get('FLASK_ENV', 'unknown'),
        'port': os.environ.get('PORT', 'unknown')
    }) 