from flask import Blueprint, request, jsonify, session, current_app
from functools import wraps
import traceback
import re
import os
from datetime import datetime
from app.database import RunDatabase, safe_json_dumps
from app.running import analyze_run_file
import json

runs_bp = Blueprint('runs_bp', __name__)
db = RunDatabase()

# Updated CustomJSONEncoder with comprehensive Infinity handling
class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        # Pre-process to handle infinity/NaN values
        def handle_special_values(item):
            if isinstance(item, float):
                if item == float('inf') or item == float('Infinity'):
                    return "Infinity"
                if item == float('-inf') or item == float('-Infinity'):
                    return "-Infinity"
                if item != item:  # NaN check
                    return "NaN"
            elif isinstance(item, dict):
                return {k: handle_special_values(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [handle_special_values(i) for i in item]
            return item
        
        processed_obj = handle_special_values(obj)
        return super().encode(processed_obj)
        
    def default(self, obj):
        if isinstance(obj, float):
            if obj == float('inf') or obj == float('Infinity'):
                return "Infinity"
            if obj == float('-inf') or obj == float('-Infinity'):
                return "-Infinity" 
            if obj != obj:  # NaN check
                return "NaN"
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
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
    """
    Get all runs for the current user
    With extreme safety measures to ensure a valid JSON array is always returned
    """
    try:
        user_id = session.get('user_id')
        print(f"Fetching runs for user: {user_id}")
        
        # Extra safety: verify user_id exists
        if not user_id:
            print("WARNING: No user_id in session")
            return jsonify([])
            
        # Get runs from database with error handling
        try:
            runs = db.get_all_runs(user_id)
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            traceback.print_exc()
            # Return empty array on DB error
            return jsonify([])
        
        # Debug logging
        print(f"Fetched runs type: {type(runs)}")
        print(f"Is runs array? {isinstance(runs, list)}")
        if runs:
            print(f"Runs count: {len(runs) if hasattr(runs, '__len__') else 'unknown'}")
            print(f"First run: {runs[0] if isinstance(runs, list) and runs else None}")
        
        # CRITICAL: Ensure we're working with a list/array
        safe_runs = []
        
        # 1. Handle None case
        if runs is None:
            print("WARNING: runs is None")
            return jsonify([])
            
        # 2. Handle list case (expected)
        if isinstance(runs, list):
            safe_runs = runs
        else:
            # 3. Try to convert to list if possible
            print(f"WARNING: runs is not a list, it's {type(runs)}")
            try:
                safe_runs = list(runs)
            except Exception as e:
                print(f"Error converting to list: {str(e)}")
                safe_runs = []
        
        # 4. Process each run to ensure it's serializable
        result = []
        for i, run in enumerate(safe_runs):
            try:
                # Skip if not a dict
                if not isinstance(run, dict):
                    print(f"WARNING: run {i} is not a dict, skipping")
                    continue
                    
                # Create a safe copy with special values handled
                safe_run = {}
                for key, value in run.items():
                    # Use a direct assignment for all types
                    safe_run[key] = value
                    
                # Add to result if not empty
                if safe_run:
                    result.append(safe_run)
            except Exception as e:
                print(f"Error processing run {i}: {e}")
                continue
        
        # Final safety check
        if not isinstance(result, list):
            print("CRITICAL ERROR: Final result is not a list!")
            return jsonify([])
            
        # Log final output
        print(f"Returning {len(result)} safe runs")
        
        # Use the SafeJSONEncoder for response
        try:
            # Convert to string manually with special value handling
            safe_json = safe_json_dumps(result)
            
            # Verify the JSON is valid by parsing it
            try:
                json.loads(safe_json)
            except json.JSONDecodeError:
                print("WARNING: Generated invalid JSON, using empty array")
                return jsonify([])
                
            # Return the safe JSON response
            return current_app.response_class(
                response=safe_json,
                status=200,
                mimetype='application/json'
            )
        except Exception as json_error:
            print(f"Error encoding JSON: {json_error}")
            # Last resort, return empty array
            return jsonify([])
            
    except Exception as e:
        print(f"Unexpected error getting runs: {str(e)}")
        traceback.print_exc()
        # Always return empty array for any error
        return jsonify([])


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
            return current_app.response_class(
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