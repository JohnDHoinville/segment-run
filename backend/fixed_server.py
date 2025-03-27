from flask import Flask, jsonify, request, session
import os
from datetime import datetime
import sys
import traceback

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'development_key')

# Just for testing - mock database object
class MockDatabase:
    def get_profile(self, user_id):
        return {'user_id': user_id, 'age': 30, 'resting_hr': 60, 'weight': 70, 'gender': 0}

db = MockDatabase()

@app.route('/')
def hello():
    """Root endpoint that returns a simple message."""
    return jsonify({
        'message': 'GPX4U Flask server is running. Try /health for more info.'
    })

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'python_version': sys.version
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    """Example of properly indented try/except block that was causing issues."""
    try:
        # Try to get the profile with a direct connection check
        try:
            profile = db.get_profile(session['user_id'])
            print("\nProfile data:", profile)
        except Exception as profile_error:
            print(f"Error getting profile: {str(profile_error)}")
            # Create default profile if fetch fails
            profile = {
                'user_id': session.get('user_id', 0),
                'age': 30,
                'resting_hr': 60,
                'weight': 70,
                'gender': 0
            }
            print(f"Using default profile: {profile}")
            
        return jsonify({
            'message': 'Analysis route is working correctly',
            'profile': profile
        })
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 