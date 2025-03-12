from flask import Blueprint, request, jsonify, session
from functools import wraps
import traceback
import re
import os
from datetime import datetime
from backend.app.database import RunDatabase
from backend.app.running import analyze_run_file
import json

runs_bp = Blueprint('runs_bp', __name__)
db = RunDatabase()

# Add a custom JSON encoder class to handle Infinity
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and (obj == float('inf') or obj == float('-inf') or obj != obj):  # last condition checks for NaN
            return str(obj)  # Convert Infinity, -Infinity and NaN to strings
        return super().default(obj)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@runs_bp.route('/runs', methods=['GET'])
@login_required
def get_runs():
    try:
        user_id = session['user_id']
        runs = db.get_all_runs(user_id)
        # Debug: Print the first run with its pace_limit
        if runs:
            print(f"First run pace_limit: {runs[0].get('pace_limit')}")
            print(f"Run pace_limit types: {[(run['id'], type(run.get('pace_limit'))) for run in runs[:3]]}")
        
        # Use the custom encoder to safely serialize the response
        return app.response_class(
            response=json.dumps(runs, cls=CustomJSONEncoder),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        print(f"Error getting runs: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@runs_bp.route('/analyze', methods=['POST'])
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
            analysis_result = analyze_run_file(temp_path, pace_limit, age, resting_hr, weight=profile.get('weight', 70))
            print("\nAnalysis completed successfully.")

            # Save the run to database
            run_id = db.add_run(
                user_id=session['user_id'],
                date=run_date,
                data=json.dumps(analysis_result, cls=CustomJSONEncoder),  # Use custom encoder here
                total_distance=analysis_result['total_distance'],
                avg_pace=analysis_result.get('avg_pace_all'),
                avg_hr=analysis_result.get('avg_hr_all'),
                pace_limit=pace_limit
            )
            print(f"Run saved successfully with ID: {run_id}")

            # Use custom encoder for the response too
            return app.response_class(
                response=json.dumps({
                    'message': 'Analysis complete',
                    'data': analysis_result,
                    'run_id': run_id,
                    'saved': True
                }, cls=CustomJSONEncoder),
                status=200,
                mimetype='application/json'
            )
            
        except Exception as e:
            print(f"\nError during analysis:")
            traceback.print_exc()
            return jsonify({'error': f'Failed to analyze run: {str(e)}'}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"Cleaned up temp file: {temp_path}")
    except Exception as e:
        print(f"\nServer error in /analyze route:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 