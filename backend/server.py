from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import tempfile
import os
from app.database import RunDatabase
from app.running import analyze_run_file, calculate_pace_zones, analyze_elevation_impact
import json
from datetime import datetime
import re
from functools import wraps
import secrets
import traceback
from json import JSONEncoder

# Use the custom encoder for all JSON responses
class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)

# Load environment variables
load_dotenv('.flaskenv')

app = Flask(__name__)
print("Starting Flask server...")

# Use the custom encoder for all JSON responses
app.json_encoder = DateTimeEncoder

# Configure session
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SESSION_COOKIE_NAME='running_session'  # Custom session cookie name
)

# Generate a secure random key
app.secret_key = secrets.token_hex(32)

# Configure CORS
CORS(app,
    origins=["http://localhost:3000"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Cookie"],  # Add Cookie to allowed headers
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization", "Set-Cookie"],  # Add Set-Cookie
    allow_credentials=True)

# Add debug logging for session
@app.before_request
def log_request_info():
    print('Headers:', dict(request.headers))
    print('Session:', dict(session))
    print('Cookies:', dict(request.cookies))

db = RunDatabase()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend server is running'}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Server is running'}), 200

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    try:
        print("\n=== Starting Analysis ===")
        if 'file' not in request.files:
            print("No file in request")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        print(f"\nFile details:")
        print(f"Filename: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"File size: {len(file.read())} bytes")
        file.seek(0)  # Reset file pointer after reading
        
        # Debug profile data
        print("\nSession data:", dict(session))
        print("User ID:", session.get('user_id'))
        
        pace_limit = float(request.form.get('paceLimit', 0))
        age = int(request.form.get('age', 0))
        resting_hr = int(request.form.get('restingHR', 0))
        
        # Get user profile for additional metrics
        profile = db.get_profile(session['user_id'])
        print("\nProfile data:", profile)
        
        if not file or not file.filename.endswith('.gpx'):
            print("Invalid file format")
            return jsonify({'error': 'Invalid file format'}), 400
            
        # Extract date from filename
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', file.filename)
        run_date = date_match.group(0) if date_match else datetime.now().strftime('%Y-%m-%d')
        
        # Save uploaded file temporarily
        temp_path = 'temp.gpx'
        file.save(temp_path)
        
        print("\nFile saved to:", temp_path)
        print("File exists:", os.path.exists(temp_path))
        print("File size:", os.path.getsize(temp_path))
        
        try:
            # Analyze the file
            analysis_result = analyze_run_file(
                temp_path, 
                pace_limit,
                user_age=age,
                resting_hr=resting_hr,
                weight=profile['weight'],
                gender=profile['gender']
            )
            
            if not analysis_result:
                print("Analysis returned no results")
                return jsonify({'error': 'Failed to analyze run data'}), 500
                
            # Build run_data to save in the runs table
            run_data = {
                'date': run_date,   # or datetime.now().strftime('%Y-%m-%d')
                'data': analysis_result
            }
            
            # Actually save the run
            print("\nAttempting to save run data...")
            run_id = db.save_run(session['user_id'], run_data)
            print(f"Run saved successfully with ID: {run_id}")

            return jsonify({
                'message': 'Analysis complete',
                'data': analysis_result,
                'run_id': run_id,
                'saved': True
            })
            
        except Exception as e:
            print(f"\nError during analysis:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full traceback:")
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"Cleaned up temporary file: {temp_path}")
                
    except Exception as e:
        print(f"\nServer error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/runs', methods=['GET'])
@login_required
def get_runs():
    try:
        print("Fetching runs for user:", session['user_id'])
        print("Session data:", dict(session))
        runs = db.get_all_runs(session['user_id'])
        print(f"Raw runs from database:", runs)
        
        # Format runs for frontend
        formatted_runs = []
        for run in runs:
            try:
                # Ensure data is parsed JSON
                run_data = run['data']
                print(f"Processing run {run['id']}, data type:", type(run_data))
                if isinstance(run_data, str):
                    run_data = json.loads(run_data)
                
                # Create formatted run object
                formatted_run = {
                    'id': run['id'],
                    'date': run['date'],
                    'data': run_data,
                    'total_distance': run['total_distance'],
                    'avg_pace': run['avg_pace'],
                    'avg_hr': run['avg_hr']
                }
                print(f"Formatted run:", formatted_run)
                formatted_runs.append(formatted_run)
            except Exception as e:
                print(f"Error formatting run {run['id']}: {str(e)}")
                traceback.print_exc()
                continue
        
        print(f"Returning {len(formatted_runs)} formatted runs")
        return jsonify(formatted_runs)
    except Exception as e:
        print(f"Error getting runs: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/compare', methods=['POST'])
@login_required
def compare_runs():
    try:
        run_ids = request.json['runIds']
        print(f"Comparing runs with IDs: {run_ids}")
        
        formatted_runs = []
        for run_id in run_ids:
            run = db.get_run_by_id(run_id)
            if run:
                try:
                    run_data = json.loads(run['data'])
                    
                    # Calculate total time for average pace
                    total_time = 0
                    for segment in run_data['fast_segments'] + run_data['slow_segments']:
                        if isinstance(segment, dict) and 'time_diff' in segment:
                            total_time += segment['time_diff']
                    
                    # Calculate average pace
                    avg_pace = total_time / run_data['total_distance'] if run_data['total_distance'] > 0 else 0
                    
                    # Calculate elevation gain
                    elevation_gain = 0
                    if 'elevation_data' in run_data:
                        elevation_changes = [point['elevation'] for point in run_data['elevation_data']]
                        elevation_gain = sum(max(0, elevation_changes[i] - elevation_changes[i-1]) 
                                          for i in range(1, len(elevation_changes)))
                    
                    formatted_run = {
                        'id': run['id'],
                        'date': run['date'],
                        'distance': run_data['total_distance'],
                        'avg_pace': avg_pace,
                        'avg_hr': run_data.get('avg_hr_all', 0),
                        'elevation_gain': elevation_gain,
                        'data': run['data'],
                        'mile_splits': run_data.get('mile_splits', [])
                    }
                    formatted_runs.append(formatted_run)
                    print(f"Formatted run for comparison: {formatted_run}")
                except Exception as e:
                    print(f"Error formatting run {run_id}: {str(e)}")
                    traceback.print_exc()
                    continue
        
        return jsonify(formatted_runs)
    except Exception as e:
        print(f"Compare error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/runs/<int:run_id>', methods=['DELETE'])
@login_required
def delete_run(run_id):
    try:
        print(f"Attempting to delete run {run_id}")
        # Verify the run belongs to the current user
        run = db.get_run_by_id(run_id, session['user_id'])
        if not run:
            print(f"Run {run_id} not found or doesn't belong to user")
            return jsonify({'error': 'Run not found'}), 404
            
        db.delete_run(run_id)
        print(f"Successfully deleted run {run_id}")
        return jsonify({'message': f'Run {run_id} deleted successfully'})
    except Exception as e:
        print(f"Error deleting run: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        profile = db.get_profile(session['user_id'])
        return jsonify(profile)
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['POST'])
@login_required
def save_profile():
    try:
        data = request.json
        age = data.get('age', 0)
        resting_hr = data.get('resting_hr', 0)
        weight = data.get('weight', 70)
        gender = data.get('gender', 1)
        
        db.save_profile(
            user_id=session['user_id'],
            age=age,
            resting_hr=resting_hr,
            weight=weight,
            gender=gender
        )
        
        return jsonify({
            'message': 'Profile saved successfully',
            'age': age,
            'resting_hr': resting_hr,
            'weight': weight,
            'gender': gender
        })
    except Exception as e:
        print(f"Error saving profile: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
            
        user_id = db.create_user(username, password)
        session['user_id'] = user_id
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id
        })
    except Exception as e:
        print(f"Registration error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Username already exists'}), 400

@app.route('/auth/login', methods=['POST'])
def login():
    try:
        print("\nReceived login request")
        data = request.json
        username = data.get('username')
        password = data.get('password')
        print(f"Login attempt for user: {username}")
        
        user_id = db.verify_user(username, password)
        if user_id:
            session['user_id'] = user_id
            session.modified = True  # Ensure session is saved
            print(f"\nLogin successful:")
            print(f"User ID: {user_id}")
            print(f"Session: {dict(session)}")
            print(f"Cookies to be set: {dict(request.cookies)}")
            return jsonify({
                'message': 'Login successful',
                'user_id': user_id
            })
        print("Login failed: Invalid credentials")
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"Login error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/auth/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Both current and new password required'}), 400
            
        if not db.update_password(session['user_id'], current_password, new_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
            
        return jsonify({'message': 'Password updated successfully'})
    except Exception as e:
        print(f"Password change error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/auth/check', methods=['GET'])
def check_auth():
    print("Received auth check request")
    try:
        if 'user_id' in session:
            print(f"User {session['user_id']} is authenticated")
            return jsonify({
                'authenticated': True,
                'user_id': session['user_id']
            })
        print("No user in session")
        return jsonify({
            'authenticated': False,
            'user_id': None
        })
    except Exception as e:
        print(f"Auth check error: {str(e)}")
        return jsonify({
            'authenticated': False,
            'error': str(e)
        }), 500

@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({'status': 'Backend server is running'})

@app.route('/debug/session', methods=['GET'])
def debug_session():
    return jsonify({
        'session': dict(session),
        'cookies': dict(request.cookies),
        'headers': dict(request.headers)
    })

if __name__ == '__main__':
    print("Starting server on http://localhost:5001")
    app.run(
        debug=True,
        host='localhost',
        port=5001,
        ssl_context=None
    ) 