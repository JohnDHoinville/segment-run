from flask import Blueprint, request, jsonify, session, current_app
from functools import wraps
import traceback
import re
import os
from datetime import datetime
from app.database import RunDatabase, safe_json_dumps
from app.running import analyze_run_file, calculate_vo2max, calculate_training_load, calculate_recovery_time
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
        print(f"\n=== Getting runs for user {session['user_id']} ===")
        runs = db.get_all_runs(session['user_id'])
        
        # 1. Basic validation - ensure we have a list
        if not runs:
            print("No runs found")
            return jsonify([])
            
        # 2. Debug info about the runs
        print(f"Found {len(runs)} runs")
        
        # Log a sample run to verify structure
        if runs:
            sample_run = runs[0]
            print("\nSample run structure:")
            print(f"ID: {sample_run.get('id')}")
            print(f"Date: {sample_run.get('date')}")
            print(f"Total Distance: {sample_run.get('total_distance')}")
            print(f"Pace Limit: {sample_run.get('pace_limit')}")
            
            # Check pace_limit specifically since that's our issue
            pace_limit = sample_run.get('pace_limit')
            print(f"Pace Limit Type: {type(pace_limit).__name__}")
            print(f"Pace Limit Value: {pace_limit}")
            
            # Debug the runs data specifically
            if 'data' in sample_run:
                data_type = type(sample_run['data']).__name__
                print(f"Data field type: {data_type}")
                
                # If data is an object, check if it has pace_limit
                if isinstance(sample_run['data'], dict):
                    data_pace_limit = sample_run['data'].get('pace_limit')
                    print(f"Data.pace_limit: {data_pace_limit}")
                    print(f"Data.pace_limit type: {type(data_pace_limit).__name__ if data_pace_limit is not None else 'None'}")
        
        # Modify each run to ensure pace_limit is available directly
        for run in runs:
            # Make sure pace_limit is directly accessible
            if ('pace_limit' not in run or run['pace_limit'] is None or run['pace_limit'] == 0) and 'data' in run:
                data = run['data']
                if isinstance(data, dict) and 'pace_limit' in data:
                    run['pace_limit'] = data['pace_limit']
                    print(f"Set direct pace_limit for run {run.get('id')} to {run['pace_limit']}")
        
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

            # Add detailed debug logging to see what exactly is being saved
            print("\n=== SAVING RUN DATA ===")
            print(f"Advanced metrics being saved:")
            print(f"VO2 Max: {analysis_result.get('vo2max')}")
            
            # Add run date to analysis results
            analysis_result['run_date'] = run_date
            
            # Save the run to database
            encoded_data = json.dumps(analysis_result, cls=CustomJSONEncoder)
            
            # Debug log the full encoded data (truncated for readability)
            print(f"Encoded data sample: {encoded_data[:100]}...")

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
            
            # Ensure all metrics are available at top level of response
            response_data = {
                'message': 'Analysis data retrieved successfully',
                'run_id': run['id'],
                'date': run['date'],
                'run_date': run['date'],
                'pace_limit': run['pace_limit'],
            }

            # Copy all run_data properties into response_data
            for key, value in run_data.items():
                response_data[key] = value
            
            # If advanced metrics are missing, try to recalculate them
            if not run_data.get('vo2max') or not run_data.get('training_load') or not run_data.get('recovery_time'):
                print("Advanced metrics missing, adding defaults to prevent UI errors")
                
                # Add placeholder metrics if missing
                profile = db.get_profile(user_id)
                
                if not run_data.get('vo2max'):
                    # Estimate VO2max using available data
                    if profile and 'age' in profile and 'weight' in profile and run_data.get('avg_hr_all') and run_data.get('total_distance'):
                        avg_hr = run_data.get('avg_hr_all', 0)
                        max_hr = run_data.get('max_hr', 220 - profile.get('age', 30))
                        avg_pace = run_data.get('avg_pace_all', 0) or run_data.get('avg_pace', 0)
                        
                        calculated_vo2max = calculate_vo2max(
                            avg_hr=avg_hr,
                            max_hr=max_hr,
                            avg_pace=avg_pace,
                            user_age=profile.get('age', 30),
                            gender=profile.get('gender', 1)
                        )
                        # Set in both places
                        run_data['vo2max'] = calculated_vo2max
                        response_data['vo2max'] = calculated_vo2max
                        print(f"Added calculated VO2max: {calculated_vo2max}")
                
                if not run_data.get('training_load'):
                    # Estimate training load using available data
                    if run_data.get('avg_hr_all') and run_data.get('total_distance'):
                        # Estimate duration from distance and pace
                        avg_pace = run_data.get('avg_pace_all', 0) or run_data.get('avg_pace', 0)
                        duration_minutes = run_data.get('total_distance', 0) * avg_pace
                        
                        resting_hr = profile.get('resting_hr', 60) if profile else 60
                        max_hr = run_data.get('max_hr', 220 - profile.get('age', 30))
                        
                        calculated_load = calculate_training_load(
                            duration_minutes=duration_minutes,
                            avg_hr=run_data.get('avg_hr_all', 0),
                            resting_hr=resting_hr,
                            max_hr=max_hr
                        )
                        # Set in both places
                        run_data['training_load'] = calculated_load
                        response_data['training_load'] = calculated_load
                        print(f"Added calculated training load: {calculated_load}")
                
                if not run_data.get('recovery_time') and (run_data.get('training_load') or response_data.get('training_load')):
                    # Estimate recovery time based on training load
                    training_load = run_data.get('training_load') or response_data.get('training_load')
                    calculated_recovery = calculate_recovery_time(
                        training_load=training_load
                    )
                    # Set in both places
                    run_data['recovery_time'] = calculated_recovery
                    response_data['recovery_time'] = calculated_recovery
                    print(f"Added calculated recovery time: {calculated_recovery}")
            
            # Double-check that the advanced metrics are included
            if 'vo2max' not in response_data and 'vo2max' in run_data:
                response_data['vo2max'] = run_data['vo2max']
                print(f"Copied vo2max to top level: {response_data['vo2max']}")
                
            if 'training_load' not in response_data and 'training_load' in run_data:
                response_data['training_load'] = run_data['training_load']
                print(f"Copied training_load to top level: {response_data['training_load']}")
                
            if 'recovery_time' not in response_data and 'recovery_time' in run_data:
                response_data['recovery_time'] = run_data['recovery_time']
                print(f"Copied recovery_time to top level: {response_data['recovery_time']}")
            
            print(f"Final response includes advanced metrics:")
            print(f"VO2 Max: {response_data.get('vo2max')}")
            print(f"Training Load: {response_data.get('training_load')}")
            print(f"Recovery Time: {response_data.get('recovery_time')}")
                
            # Return the full analysis data with updates
            return safe_json_dumps(response_data), 200
            
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid run data format'}), 500
            
    except Exception as e:
        print(f"Error retrieving run analysis: {str(e)}")
        traceback.print_exc()  # Add detailed stack trace for debugging
        return jsonify({'error': 'Failed to retrieve analysis data'}), 500 