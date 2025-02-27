from flask import Flask, request, jsonify, session
from flask_cors import CORS
import tempfile
import os
from running import analyze_run_file, calculate_pace_zones, analyze_elevation_impact
import traceback
from database import RunDatabase
import json
from datetime import datetime
import re
from functools import wraps
import secrets  # Add this import

app = Flask(__name__)

# Configure session
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)

# Generate a secure random key
app.secret_key = secrets.token_hex(32)

# Update CORS configuration
CORS(app,
    origins=["http://localhost:3000"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization"],
    allow_credentials=True)  # Add this line

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
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        pace_limit = float(request.form.get('paceLimit', 0))
        age = int(request.form.get('age', 0))
        resting_hr = int(request.form.get('restingHR', 0))
        
        if not file or not file.filename.endswith('.gpx'):
            return jsonify({'error': 'Invalid file format'}), 400
            
        # Extract date from filename
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', file.filename)
        run_date = date_match.group(0) if date_match else datetime.now().strftime('%Y-%m-%d')
        
        # Save uploaded file temporarily
        temp_path = 'temp.gpx'
        file.save(temp_path)
        
        try:
            # Analyze the file
            results = analyze_run_file(temp_path, pace_limit, age, resting_hr)
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Calculate average pace
        total_time = 0
        for segment in results['fast_segments'] + results['slow_segments']:
            if isinstance(segment, dict) and 'time_diff' in segment:
                total_time += segment['time_diff']
        
        # Format run data for database
        run_data = {
            'date': run_date,
            'total_distance': results['total_distance'],
            'avg_pace': total_time / results['total_distance'] if results['total_distance'] > 0 else 0,
            'avg_hr_all': results['avg_hr_all'],
            'data': results  # Store the entire results object
        }
        
        print(f"User ID from session: {session['user_id']}")  # Debug print
        print("Attempting to save run...")  # Debug print
        
        # Save run to database with user_id
        try:
            db.save_run(session['user_id'], run_data)
            print("Run saved successfully")
            results['saved'] = True
            results['save_message'] = 'Run saved successfully'
        except Exception as e:
            print(f"Error saving run: {str(e)}")
            results['saved'] = False
            results['save_message'] = 'Error saving run'
            
        # Get recent runs for comparison
        recent_runs = db.get_recent_runs(session['user_id'])
        
        # Add pace zones
        results['pace_zones'] = calculate_pace_zones(recent_runs)
        
        # Add elevation analysis
        results['elevation_impact'] = analyze_elevation_impact(results['route_data'])
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e), 'saved': False}), 500

@app.route('/runs', methods=['GET'])
@login_required
def get_runs():
    try:
        print("Fetching runs for user:", session['user_id'])
        runs = db.get_all_runs(session['user_id'])
        print(f"Found {len(runs)} runs for user")
        
        # Format runs for frontend
        formatted_runs = []
        for run in runs:
            print(f"Processing run: {run}")
            try:
                run_data = json.loads(run['data'])  # Parse stored JSON data
                
                # Calculate total time for average pace
                total_time = 0
                for segment in run_data['fast_segments'] + run_data['slow_segments']:
                    if isinstance(segment, dict) and 'time_diff' in segment:
                        total_time += segment['time_diff']
                
                # Calculate average pace
                avg_pace = total_time / run_data['total_distance'] if run_data['total_distance'] > 0 else 0
                
                formatted_run = {
                    'id': run['id'],
                    'date': run['date'],
                    'distance': run_data['total_distance'],
                    'avg_pace': avg_pace,  # Use calculated average pace
                    'avg_hr': run_data.get('avg_hr_all', 0),
                    'type': 'Training',
                    'data': run['data']
                }
                formatted_runs.append(formatted_run)
                print(f"Formatted run: {formatted_run}")
            except Exception as e:
                print(f"Error formatting run {run['id']}: {str(e)}")
                continue
                
        print(f"Returning {len(formatted_runs)} formatted runs")
        return jsonify(formatted_runs)
    except Exception as e:
        print(f"Error getting runs: {str(e)}")
        traceback.print_exc()
        return jsonify([])

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
        
        db.save_profile(session['user_id'], age, resting_hr)
        
        return jsonify({
            'message': 'Profile saved successfully',
            'age': age,
            'resting_hr': resting_hr
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
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        user_id = db.verify_user(username, password)
        if user_id:
            session['user_id'] = user_id
            session.modified = True  # Ensure session is saved
            print(f"Login successful. Session: {dict(session)}")  # Debug print
            return jsonify({
                'message': 'Login successful',
                'user_id': user_id
            })
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

if __name__ == '__main__':
    print("Starting server on http://localhost:5001")
    app.run(
        debug=True,
        host='localhost',  # Change from '0.0.0.0' to 'localhost'
        port=5001,
        ssl_context=None  # Explicitly disable SSL for local development
    ) 