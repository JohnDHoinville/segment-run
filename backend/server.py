from flask import Flask, request, jsonify, session, send_from_directory
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
from app import app

# Use the custom encoder for all JSON responses
class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        return super().default(obj)

# Load environment variables
load_dotenv('.flaskenv')

print("Starting Flask server...")
print(f"Current working directory: {os.getcwd()}")

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
    origins=["http://localhost:3000", "https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization", "Cache-Control"],
    resources={
        r"/*": {
            "origins": ["http://localhost:3000", "https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"],
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Cache-Control"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization", "Cache-Control"]
        }
    }
)

# Add debug logging for session
@app.before_request
def log_request_info():
    print('\n=== Request Details ===')
    print(f'URL: {request.url}')
    print(f'Method: {request.method}')
    print(f'Path: {request.path}')
    print(f'Headers: {dict(request.headers)}')
    print(f'Session: {dict(session)}')
    print(f'Cookies: {dict(request.cookies)}')
    print('=====================\n')

db = RunDatabase()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        print(f"\n=== Static File Request ===")
        print(f"Requested file: {filename}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Get request origin
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"]
        
        # Determine file type for correct directory handling
        file_type = None
        if '/' in filename:
            parts = filename.split('/')
            if len(parts) > 1:
                file_type = parts[0]  # css or js or media
                
        # Try different locations based on file type
        if file_type:
            # Handle nested paths like css/main.123.css
            if os.path.exists(os.path.join('static', filename)):
                response = send_from_directory('static', filename)
            else:
                print(f"File not found in static directory: {filename}")
                return jsonify({"error": "File not found"}), 404
        else:
            # Direct files like main.css
            if os.path.exists(os.path.join('static', 'css', filename)):
                response = send_from_directory(os.path.join('static', 'css'), filename)
            elif os.path.exists(os.path.join('static', 'js', filename)):
                response = send_from_directory(os.path.join('static', 'js'), filename)
            elif os.path.exists(os.path.join('static', 'media', filename)):
                response = send_from_directory(os.path.join('static', 'media'), filename)
            elif os.path.exists(os.path.join('static', filename)):
                response = send_from_directory('static', filename)
            else:
                print(f"File not found in any static directory: {filename}")
                return jsonify({"error": "File not found"}), 404
            
        # Set CORS headers for all responses
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            # Default to the production domain
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
        # Set content type headers based on file extension
        if filename.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'
        elif filename.endswith('.css'):
            response.headers['Content-Type'] = 'text/css'
        elif filename.endswith('.png'):
            response.headers['Content-Type'] = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            response.headers['Content-Type'] = 'image/jpeg'
        elif filename.endswith('.svg'):
            response.headers['Content-Type'] = 'image/svg+xml'
        elif filename.endswith('.woff'):
            response.headers['Content-Type'] = 'font/woff'
        elif filename.endswith('.woff2'):
            response.headers['Content-Type'] = 'font/woff2'
        elif filename.endswith('.ttf'):
            response.headers['Content-Type'] = 'font/ttf'
        elif filename.endswith('.ico'):
            response.headers['Content-Type'] = 'image/x-icon'
        
        # Add caching headers for static assets
        response.headers['Cache-Control'] = 'public, max-age=31536000'
                
        return response
        
    except Exception as e:
        print(f"Error serving static file {filename}: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    try:
        print(f"\n=== React App Request ===")
        print(f"Requested path: {path}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Get origin for CORS
        origin = request.headers.get('Origin', '')
        allowed_origins = ["http://localhost:3000", "https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"]
        
        # Handle static file requests directly
        if path.startswith('static/'):
            static_path = path[7:]  # Remove 'static/' prefix
            return serve_static(static_path)
        
        # API paths that should be handled by the backend routes
        api_paths = ['analyze', 'login', 'register', 'profile', 'runs', 'compare', 'logout', 'test']
        
        # For non-API routes, serve index.html (React routing will handle it)
        if path and any(path.startswith(api_path) for api_path in api_paths):
            # Let Flask handle API routes
            print(f"API route detected: {path}")
            return app.response_class(
                response="API Endpoint",
                status=404
            )
        
        # If we get here, serve the React app (let React Router handle client-side routing)
        try:
            # Try different possible locations for index.html
            if os.path.exists('templates/index.html'):
                print("Serving index.html from templates directory")
                
                # Read the file and send it directly to avoid path issues
                with open('templates/index.html', 'r') as f:
                    content = f.read()
                
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='text/html'
                )
            else:
                print("No index.html found, creating fallback HTML page")
                html = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="utf-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1" />
                    <title>GPX4U - Running Analysis</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 0; }
                        .app { max-width: 960px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }
                        h1 { margin: 0; }
                        p { line-height: 1.6; color: #333; }
                        .container { background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    </style>
                </head>
                <body>
                    <div class="app">
                        <div class="header">
                            <h1>GPX4U Running Analysis</h1>
                        </div>
                        <div class="container">
                            <h2>Welcome to GPX4U</h2>
                            <p>Your running data analysis platform is being configured.</p>
                            <p>Please check back shortly or contact support if you continue to see this message.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                response = app.response_class(
                    response=html,
                    status=200,
                    mimetype='text/html'
                )
        except Exception as inner_e:
            print(f"Error serving index.html: {str(inner_e)}")
            traceback.print_exc()
            # Return a simple HTML page on error
            html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>GPX4U - Running Analysis</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 0; }
                    .app { max-width: 960px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }
                    h1 { margin: 0; }
                    p { line-height: 1.6; color: #333; }
                    .container { background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                </style>
            </head>
            <body>
                <div class="app">
                    <div class="header">
                        <h1>GPX4U Running Analysis</h1>
                    </div>
                    <div class="container">
                        <h2>Welcome to GPX4U</h2>
                        <p>Your running data analysis platform is being configured.</p>
                        <p>Please check back shortly or contact support if you continue to see this message.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            response = app.response_class(
                response=html,
                status=200,
                mimetype='text/html'
            )
        
        # Set CORS headers
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
        
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
        # Don't cache index.html
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"Critical error serving app: {str(e)}")
        traceback.print_exc()
        
        # Return a simple HTML page on critical error
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>GPX4U - Running Analysis</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 0; }
                .app { max-width: 960px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }
                h1 { margin: 0; }
                p { line-height: 1.6; color: #333; }
                .container { background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="app">
                <div class="header">
                    <h1>GPX4U Running Analysis</h1>
                </div>
                <div class="container">
                    <h2>Welcome to GPX4U</h2>
                    <p>Your running data analysis platform is being configured.</p>
                    <p>Please check back shortly or contact support if you continue to see this message.</p>
                </div>
            </div>
        </body>
        </html>
        """
        response = app.response_class(
            response=html,
            status=200,
            mimetype='text/html'
        )
        
        # Try to set CORS headers even on error
        try:
            origin = request.headers.get('Origin', '')
            allowed_origins = ["http://localhost:3000", "https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"]
            
            if origin in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'
        except:
            pass
            
        return response

@app.route('/test', methods=['GET'])
def test():
    try:
        import os
        import sys
        
        # Get basic system info
        current_dir = os.getcwd()
        dir_contents = os.listdir(current_dir)
        
        # Safely get directory contents
        def safe_listdir(path):
            try:
                return os.listdir(path) if os.path.exists(path) else []
            except Exception as e:
                return [f"Error: {str(e)}"]
        
        # Check various directories
        static_contents = safe_listdir('static')
        templates_contents = safe_listdir('templates')
        backend_static_contents = safe_listdir('backend/static')
        
        return jsonify({
            'status': 'Backend server is running',
            'python_version': sys.version,
            'current_directory': current_dir,
            'directory_contents': dir_contents,
            'static_directory_contents': static_contents,
            'templates_directory_contents': templates_contents,
            'backend_static_contents': backend_static_contents,
            'env_variables': {k: v for k, v in os.environ.items() if not k.startswith('AWS') and not k.startswith('SECRET')}
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'Error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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

# Handle favicon.ico requests to prevent 404/500 errors
@app.route('/favicon.ico')
def favicon():
    try:
        # Try different possible locations for favicon.ico
        if os.path.exists('static/favicon.ico'):
            response = send_from_directory('static', 'favicon.ico')
        elif os.path.exists('public/favicon.ico'):
            response = send_from_directory('public', 'favicon.ico')
        else:
            # Return an empty response if favicon doesn't exist
            response = app.response_class(
                response='',
                status=204,
            )
            
        # Set proper content type and cache headers
        response.headers['Content-Type'] = 'image/x-icon'
        response.headers['Cache-Control'] = 'public, max-age=31536000'
        return response
    except Exception as e:
        print(f"Error serving favicon: {str(e)}")
        # Return empty response on error
        return app.response_class(
            response='',
            status=204,
        )

# Handle manifest.json, robots.txt and other root static files
@app.route('/manifest.json')
@app.route('/robots.txt')
@app.route('/logo192.png')
@app.route('/logo512.png')
def handle_react_static_files():
    try:
        # Get the filename from the request path
        filename = request.path.lstrip('/')
        
        # Check if the file exists in the static directory
        if os.path.exists(os.path.join('static', filename)):
            response = send_from_directory('static', filename)
            
            # Set proper cache headers
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            
            # Set appropriate content type
            if filename.endswith('.json'):
                response.headers['Content-Type'] = 'application/json'
            elif filename.endswith('.txt'):
                response.headers['Content-Type'] = 'text/plain'
            elif filename.endswith('.png'):
                response.headers['Content-Type'] = 'image/png'
                
            return response
        else:
            # Return empty response if file doesn't exist
            return app.response_class(
                response='',
                status=204
            )
    except Exception as e:
        print(f"Error serving static file {filename}: {str(e)}")
        return app.response_class(
            response='',
            status=204
        )

if __name__ == '__main__':
    print("Starting server on http://localhost:5001")
    app.run(
        debug=True,
        host='localhost',
        port=5001,
        ssl_context=None
    ) 