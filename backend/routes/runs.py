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
            # Pass age, resting_hr, weight, and gender to analyze_run_file
            analysis_result = analyze_run_file(
                temp_path, 
                pace_limit, 
                user_age=age, 
                resting_hr=resting_hr, 
                weight=profile.get('weight', 70),
                gender=profile.get('gender', 1)
            )
            print("\nAnalysis completed successfully.")
            
            # Log advanced metrics to verify they exist in analysis_result
            print("\nAdvanced metrics in analysis_result:")
            print(f"VO2 Max: {analysis_result.get('vo2max')}")
            print(f"Training Load: {analysis_result.get('training_load')}")
            print(f"Recovery Time: {analysis_result.get('recovery_time')}")
            print(f"Training Zones: {analysis_result.get('training_zones') is not None}")

            # Save the run to database
            # Ensure analysis_result is encoded properly to preserve all metrics
            encoded_data = json.dumps(analysis_result, cls=CustomJSONEncoder)
            
            run_id = db.add_run(
                user_id=session['user_id'],
                date=run_date,
                data=encoded_data,
                total_distance=analysis_result['total_distance'],
                avg_pace=analysis_result.get('avg_pace_all', 0),
                avg_hr=analysis_result.get('avg_hr_all', 0),
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

@runs_bp.route('/run/<int:run_id>/analysis', methods=['GET'])
def get_run_analysis(run_id):
    """
    Fetch the full analysis data for a specific run.
    
    This endpoint allows users to view previously performed analyses
    without having to re-analyze the GPX file.
    """
    # Check authentication
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Get the run directly using the RunDatabase API
        run = db.get_run(run_id, user_id)
        
        if not run:
            return jsonify({'error': 'Run not found or access denied'}), 404
        
        # Parse the data JSON
        try:
            # Get the data as a Python object
            if isinstance(run['data'], str):
                run_data = json.loads(run['data'])
            else:
                run_data = run['data']
            
            # Log what's being retrieved for debugging
            print(f"\nRetrieving run analysis for run_id: {run_id}")
            print(f"Advanced metrics in retrieved data:")
            print(f"VO2 Max: {run_data.get('vo2max')}")
            print(f"Training Load: {run_data.get('training_load')}")
            print(f"Recovery Time: {run_data.get('recovery_time')}")
            print(f"Training Zones: {run_data.get('training_zones') is not None}")
            
            # If advanced metrics are missing, try to recalculate them
            if not run_data.get('vo2max') or not run_data.get('training_load') or not run_data.get('recovery_time'):
                print("Advanced metrics missing, adding defaults to prevent UI errors")
                
                # Add placeholder metrics if missing
                profile = db.get_profile(user_id)
                
                if not run_data.get('vo2max'):
                    # Estimate VO2max using available data
                    if profile and 'age' in profile and 'weight' in profile and run_data.get('avg_hr_all') and run_data.get('total_distance'):
                        from app.running import calculate_vo2max
                        avg_hr = run_data.get('avg_hr_all', 0)
                        max_hr = run_data.get('max_hr', 220 - profile.get('age', 30))
                        avg_pace = run_data.get('avg_pace_all', 0) or run_data.get('avg_pace', 0)
                        
                        run_data['vo2max'] = calculate_vo2max(
                            avg_hr=avg_hr,
                            max_hr=max_hr,
                            avg_pace=avg_pace,
                            user_age=profile.get('age', 30),
                            gender=profile.get('gender', 1)
                        )
                        print(f"Added calculated VO2max: {run_data['vo2max']}")
                
                if not run_data.get('training_load'):
                    # Estimate training load using available data
                    if run_data.get('avg_hr_all') and run_data.get('total_distance'):
                        from app.running import calculate_training_load
                        # Estimate duration from distance and pace
                        avg_pace = run_data.get('avg_pace_all', 0) or run_data.get('avg_pace', 0)
                        duration_minutes = run_data.get('total_distance', 0) * avg_pace
                        
                        resting_hr = profile.get('resting_hr', 60) if profile else 60
                        max_hr = run_data.get('max_hr', 220 - profile.get('age', 30))
                        
                        run_data['training_load'] = calculate_training_load(
                            duration_minutes=duration_minutes,
                            avg_hr=run_data.get('avg_hr_all', 0),
                            resting_hr=resting_hr,
                            max_hr=max_hr
                        )
                        print(f"Added calculated training load: {run_data['training_load']}")
                
                if not run_data.get('recovery_time') and run_data.get('training_load'):
                    # Estimate recovery time based on training load
                    from app.running import calculate_recovery_time
                    run_data['recovery_time'] = calculate_recovery_time(
                        training_load=run_data.get('training_load', 0)
                    )
                    print(f"Added calculated recovery time: {run_data['recovery_time']}")
            
            # Return the full analysis data with updates
            return safe_json_dumps({
                'message': 'Analysis data retrieved successfully',
                'run_id': run['id'],
                'date': run['date'],
                'pace_limit': run['pace_limit'],
                **run_data  # Unpack all the analysis data
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid run data format'}), 500
            
    except Exception as e:
        print(f"Error retrieving run analysis: {str(e)}")
        traceback.print_exc()  # Add detailed stack trace for debugging
        return jsonify({'error': 'Failed to retrieve analysis data'}), 500 