from flask import Flask, request, jsonify, session, send_from_directory, make_response, send_file
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
try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except (ImportError, SystemError) as e:
    print(f"PostgreSQL support disabled: {str(e)}")
    POSTGRES_AVAILABLE = False
import sys

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

# Define allowed origins with localhost explicitly included
ALLOWED_ORIGINS = [
    "https://gpx4u.com", 
    "http://gpx4u.com", 
    "https://gpx4u-0460cd678569.herokuapp.com", 
    "http://localhost:3000",
    "http://127.0.0.1:3000",  # Additional local development URLs
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "*"  # During local development, we'll allow all origins
]

# Configure CORS
CORS(app,
    origins=ALLOWED_ORIGINS,
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],
    supports_credentials=True,
    expose_headers=["Content-Type", "Authorization", "Cache-Control"],
    max_age=3600,
    resources={
        r"/*": {
            "origins": ALLOWED_ORIGINS,
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

@app.before_request
def handle_preflight():
    # Handle OPTIONS requests for CORS preflight
    if request.method == "OPTIONS":
        print(f"Handling OPTIONS preflight request for: {request.path}")
        origin = request.headers.get("Origin", "*")
        
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", 
                           "Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Max-Age", "3600")
        print(f"OPTIONS response headers: {dict(response.headers)}")
        return response

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
        
        # Set CORS headers 
        headers = {
            'Cache-Control': 'public, max-age=31536000',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
            'Vary': 'Origin'
        }
        
        # Handle specific content types
        if filename.endswith('.js'):
            headers['Content-Type'] = 'application/javascript'
        elif filename.endswith('.css'):
            headers['Content-Type'] = 'text/css'
        elif filename.endswith('.png'):
            headers['Content-Type'] = 'image/png'
        elif filename.endswith('.svg'):
            headers['Content-Type'] = 'image/svg+xml'
        elif filename.endswith('.json'):
            headers['Content-Type'] = 'application/json'
            
        # Search paths in order of preference
        search_dirs = [
            'static',
            'backend/static',
            os.path.join(os.getcwd(), 'static'),
            os.path.join(os.getcwd(), 'backend/static')
        ]
        
        # For JS and CSS files, check subdirectories too
        if filename.startswith('js/') or filename.startswith('css/'):
            # Split path to get the directory and actual filename
            parts = filename.split('/')
            if len(parts) > 1:
                subdir = parts[0]  # 'js' or 'css'
                file_name = parts[-1]  # Just the filename without path
                
                # Add specific subdirectory paths
                search_dirs.extend([
                    os.path.join('static', subdir),
                    os.path.join('backend/static', subdir)
                ])
                
                # Try to serve the file directly from subdirectories
                for search_dir in search_dirs:
                    file_path = os.path.join(search_dir, file_name)
                    if os.path.exists(file_path):
                        print(f"Found file at: {file_path}")
                        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), headers=headers)
        
        # Try each search directory for the full path
        for search_dir in search_dirs:
            file_path = os.path.join(search_dir, filename)
            if os.path.exists(file_path):
                print(f"Found file at: {file_path}")
                return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), headers=headers)
            
        # If still not found, check for similar filenames in js and css directories
        if filename.endswith('.js'):
            js_dir = os.path.join('backend/static/js')
            if os.path.exists(js_dir):
                base_name = os.path.basename(filename).split('.')[0]  # e.g., 'main' from 'main.4908f7be.js'
                for file in os.listdir(js_dir):
                    if file.startswith(f"{base_name}.") and file.endswith('.js'):
                        print(f"Found similar JS file: {file}")
                        return send_from_directory(js_dir, file, headers=headers)
                        
        if filename.endswith('.css'):
            css_dir = os.path.join('backend/static/css')
            if os.path.exists(css_dir):
                base_name = os.path.basename(filename).split('.')[0]  # e.g., 'main' from 'main.42f26821.css'
                for file in os.listdir(css_dir):
                    if file.startswith(f"{base_name}.") and file.endswith('.css'):
                        print(f"Found similar CSS file: {file}")
                        return send_from_directory(css_dir, file, headers=headers)
        
        # Log if file not found
        print(f"File not found: {filename}")
        print(f"Search directories: {search_dirs}")
        if os.path.exists('backend/static'):
            print(f"Files in backend/static: {os.listdir('backend/static')}")
        if os.path.exists('backend/static/js'):
            print(f"Files in backend/static/js: {os.listdir('backend/static/js')}")
        if os.path.exists('backend/static/css'):
            print(f"Files in backend/static/css: {os.listdir('backend/static/css')}")
        
        return jsonify({"error": f"File not found: {filename}"}), 404
            
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
        
        # Handle static file requests directly
        if path.startswith('static/'):
            static_path = path[7:]  # Remove 'static/' prefix
            return serve_static(static_path)
        
        # API paths that should be handled by the backend routes
        api_paths = ['analyze', 'login', 'register', 'profile', 'runs', 'compare', 'logout', 'test', 'health', 'api', 'auth']
        
        # For API routes, let the other routes handle it
        if path and any(path.startswith(api_path) for api_path in api_paths):
            # Just return to let the proper route handler take care of it
            print(f"API route detected: {path}, letting the proper handler take care of it")
            return
        
        # If we get here, serve the React app (let React Router handle client-side routing)
        try:
            # Try different possible locations for index.html
            index_path = os.path.join('templates', 'index.html')
            if os.path.exists(index_path):
                print(f"Serving index.html from {index_path}")
                
                # Read the file and send it directly to avoid path issues
                with open(index_path, 'r') as f:
                    content = f.read()
                
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='text/html'
                )
                
                # Set headers explicitly to prevent caching
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                
                return response
            else:
                print("No index.html found, checking in backend/templates")
                backend_index_path = os.path.join('backend', 'templates', 'index.html')
                if os.path.exists(backend_index_path):
                    print(f"Serving index.html from {backend_index_path}")
                    with open(backend_index_path, 'r') as f:
                        content = f.read()
                    
                    response = app.response_class(
                        response=content,
                        status=200,
                        mimetype='text/html'
                    )
                    
                    # Set headers explicitly to prevent caching
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    
                    return response
                
                print("No index.html found, creating fallback HTML page")
                html = """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="utf-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1" />
                    <title>GPX4U - Running Analysis</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
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
                            <p>Your running data analysis platform is ready.</p>
                            <p>Please check the API documentation for available endpoints.</p>
                            <p><a href="/health">Check API Status</a></p>
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
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
                    .app { max-width: 960px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }
                    h1 { margin: 0; }
                    p { line-height: 1.6; color: #333; }
                    .container { background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .error { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; }
                </style>
            </head>
            <body>
                <div class="app">
                    <div class="header">
                        <h1>GPX4U Running Analysis</h1>
                    </div>
                    <div class="container">
                        <h2>Application Error</h2>
                        <div class="error">
                            <p>Sorry, we encountered an error loading the application.</p>
                            <p>Error details: """ + str(inner_e) + """</p>
                        </div>
                        <p>Please try again later or contact support if the issue persists.</p>
                        <p><a href="/health">Check API Status</a></p>
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
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
        
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
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
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
                .app { max-width: 960px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }
                h1 { margin: 0; }
                p { line-height: 1.6; color: #333; }
                .container { background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .error { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="app">
                <div class="header">
                    <h1>GPX4U Running Analysis</h1>
                </div>
                <div class="container">
                    <h2>Critical Application Error</h2>
                    <div class="error">
                        <p>Sorry, we encountered a critical error serving the application.</p>
                        <p>Error details: """ + str(e) + """</p>
                    </div>
                    <p>Please try again later or contact support if the issue persists.</p>
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
            allowed_origins = ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com"]
            
            if origin in ALLOWED_ORIGINS:
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
        
        # Check js and css subdirectories
        js_contents = safe_listdir('static/js')
        css_contents = safe_listdir('static/css')
        
        return jsonify({
            'status': 'Backend server is running',
            'python_version': sys.version,
            'current_directory': current_dir,
            'directory_contents': dir_contents,
            'static_directory_contents': static_contents,
            'static_js_contents': js_contents,
            'static_css_contents': css_contents,
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
        print(f"SERVER RUNNING FROM: {os.getcwd()}")
        print(f"SESSION: {dict(session)}")
        
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
        
        # Get form data with proper default values to avoid conversion errors
        pace_limit_str = request.form.get('paceLimit', '0')
        age_str = request.form.get('age', '0')
        resting_hr_str = request.form.get('restingHR', '0')
        
        # Convert to proper types with error handling
        try:
            pace_limit = float(pace_limit_str) if pace_limit_str.strip() else 0
        except ValueError:
            pace_limit = 0
            
        try:
            age = int(age_str) if age_str.strip() else 0
        except ValueError:
            age = 0
            
        try:
            resting_hr = int(resting_hr_str) if resting_hr_str.strip() else 0
        except ValueError:
            resting_hr = 0
            
        print(f"Processed form data: pace_limit={pace_limit}, age={age}, resting_hr={resting_hr}")
        
        # Get user profile for additional metrics
        # Force database reset to ensure a clean connection
        db.conn = None
        db.cursor = None
        db.connect()
        print("\n=== Database connection refreshed ===")
        
        # Try to get the profile with a direct connection check
        try:
            profile = db.get_profile(session['user_id'])
            print("\nProfile data:", profile)
        except Exception as profile_error:
            print(f"Error getting profile: {str(profile_error)}")
            # Create default profile if fetch fails
            profile = {
                'user_id': session['user_id'],
                'age': 30,
                'resting_hr': 60,
                'weight': 70,
                'gender': 0
            }
            print(f"Using default profile: {profile}")
        
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
        
        analysis_result = None
        was_saved = False
        run_id = None
        
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
                
            # Calculate totals for database storage
            total_distance = analysis_result.get('total_distance', 0)
            avg_pace = analysis_result.get('avg_pace_all', 0)
            avg_hr = analysis_result.get('avg_hr_all', 0)
                
            # Build run_data to save in the runs table
            run_data = {
                'date': run_date,
                'data': analysis_result,
                'total_distance': total_distance,
                'avg_pace': avg_pace,
                'avg_hr': avg_hr,
                'pace_limit': pace_limit
            }
            
            # Check database connection before saving
            print("\n=== DATABASE INFO ===")
            print(f"DATABASE_URL env var exists: {'DATABASE_URL' in os.environ}")
            print(f"Is using PostgreSQL: {isinstance(db.conn, psycopg2.extensions.connection) if 'psycopg2' in sys.modules else 'psycopg2 not imported'}")
            print(f"Database type: {type(db.conn).__name__}")
            
            # Force a database reconnection
            db.conn = None
            db.cursor = None
            db.connect()
            print("Database connection reset to ensure a fresh connection")
            
            # Actually save the run
            print("\nAttempting to save run data to database...")
            print(f"User ID: {session['user_id']}")
            print(f"Run date: {run_date}")
            print(f"Run distance: {total_distance}")
            
            user_id = session.get('user_id')
            if not user_id:
                print("ERROR: No user_id in session!")
                return jsonify({'error': 'User not authenticated'}), 401
                
            # Add direct database test
            try:
                print("\n=== DIRECT DATABASE TEST ===")
                if isinstance(db.conn, psycopg2.extensions.connection):
                    # PostgreSQL test
                    db.cursor.execute("SELECT current_database(), current_user")
                    test_result = db.cursor.fetchone()
                    print(f"PostgreSQL database: {test_result[0]}, user: {test_result[1]}")
                    
                    # Test tables
                    db.cursor.execute("SELECT COUNT(*) FROM runs")
                    count = db.cursor.fetchone()[0]
                    print(f"Total runs in database: {count}")
                    
                    # Test user's runs
                    db.cursor.execute("SELECT COUNT(*) FROM runs WHERE user_id = %s", (user_id,))
                    user_count = db.cursor.fetchone()[0]
                    print(f"Runs for user {user_id}: {user_count}")
                else:
                    # SQLite test
                    db.cursor.execute("SELECT COUNT(*) FROM runs")
                    count = db.cursor.fetchone()[0]
                    print(f"Total runs in database: {count}")
                    
                    # Test user's runs
                    db.cursor.execute("SELECT COUNT(*) FROM runs WHERE user_id = ?", (user_id,))
                    user_count = db.cursor.fetchone()[0]
                    print(f"Runs for user {user_id}: {user_count}")
            except Exception as db_test_error:
                print(f"Database test error: {str(db_test_error)}")
                print(traceback.format_exc())
            
            # Number of save attempts
            max_save_attempts = 3
            save_attempts = 0
            
            while save_attempts < max_save_attempts:
                save_attempts += 1
                print(f"\nSave attempt #{save_attempts}")
                
                try:
                    # Different approaches based on attempt number
                    if save_attempts == 1:
                        # First attempt - full data
                        run_id = db.save_run(user_id, run_data)
                    elif save_attempts == 2:
                        # Second attempt - simplified data
                        print("Trying simplified data...")
                        simplified_data = {
                            'date': run_date,
                            'data': {
                                'total_distance': total_distance,
                                'avg_pace': avg_pace,
                                'avg_hr': avg_hr,
                                'simplified': True
                            },
                            'total_distance': total_distance,
                            'avg_pace': avg_pace,
                            'avg_hr': avg_hr,
                            'pace_limit': pace_limit
                        }
                        run_id = db.save_run(user_id, simplified_data)
                    else:
                        # Last attempt - minimal data
                        print("Trying minimal data...")
                        minimal_data = {
                            'date': run_date,
                            'data': json.dumps({
                                'total_distance': total_distance,
                                'avg_pace': avg_pace,
                                'avg_hr': avg_hr,
                                'minimal': True
                            }),
                            'total_distance': total_distance,
                            'avg_pace': avg_pace,
                            'avg_hr': avg_hr,
                            'pace_limit': pace_limit
                        }
                        run_id = db.save_run(user_id, minimal_data)
                
                    # Check if save was successful
                    if run_id:
                        print(f"Run saved successfully with ID: {run_id} on attempt #{save_attempts}")
                        was_saved = True
                        break
                    else:
                        print(f"Save attempt #{save_attempts} failed")
                        # Force database reconnection between attempts
                        db.conn = None
                        db.cursor = None
                        db.connect()
                except Exception as save_error:
                    print(f"Error during save attempt #{save_attempts}: {str(save_error)}")
                    traceback.print_exc()
                    # Force database reconnection between attempts
                    try:
                        db.conn = None
                        db.cursor = None
                        db.connect()
                    except:
                        print("Failed to reconnect database after save error")
            
            if not was_saved:
                print("\nWARNING: Failed to save run after all attempts")
            
            # Try to verify save was successful
            if run_id:
                try:
                    # Force connection refresh before verification
                    db.conn = None
                    db.cursor = None
                    db.connect()
                    
                    test_run = db.get_run_by_id(run_id)
                    if test_run:
                        print(f"Verified run was saved correctly with ID: {run_id}")
                        was_saved = True
                    else:
                        print(f"WARNING: Could not verify run with ID {run_id}")
                        was_saved = False
                except Exception as verify_error:
                    print(f"Error verifying run: {str(verify_error)}")
                    traceback.print_exc()
                    was_saved = False
            
            # Return analysis results with detailed save status
            response = jsonify({
                'message': 'Analysis complete',
                'data': analysis_result,
                'run_id': run_id if run_id else 0,
                'saved': was_saved,
                'save_attempts': save_attempts,
                'save_error': None if was_saved else "Failed to save run data after multiple attempts",
                'distance': total_distance,
                'avg_pace': avg_pace,
                'avg_hr': avg_hr
            })
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'
            
            return response
            
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
        print(f"Getting profile for user ID: {session['user_id']}")
        profile = db.get_profile(session['user_id'])
        
        # If profile is None, create a default profile
        if profile is None:
            print(f"No profile found for user {session['user_id']}, creating default")
            db.save_profile(
                user_id=session['user_id'],
                age=30,  # Default values
                resting_hr=60,
                weight=70,
                gender=0
            )
            profile = {
                'user_id': session['user_id'],
                'age': 30,
                'resting_hr': 60,
                'weight': 70,
                'gender': 0
            }
        
        response = jsonify(profile)
        
        # Set CORS headers for profile response
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
        return response
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        
        return error_response, 500

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

@app.route('/manifest.json')
def serve_manifest():
    try:
        print("Serving manifest.json")
        
        # Create a basic manifest
        manifest = {
            "short_name": "GPX4U",
            "name": "GPX4U Running Analysis",
            "icons": [
                {
                    "src": "/static/logo192.png",
                    "type": "image/png",
                    "sizes": "192x192"
                },
                {
                    "src": "/static/logo512.png",
                    "type": "image/png",
                    "sizes": "512x512"
                }
            ],
            "start_url": "/",
            "display": "standalone",
            "theme_color": "#4285f4",
            "background_color": "#ffffff"
        }
        
        response = jsonify(manifest)
        response.headers.set('Content-Type', 'application/json')
        response.headers.set('Cache-Control', 'public, max-age=86400')
        return response
    except Exception as e:
        print(f"Error serving manifest.json: {e}")
        return jsonify({
            "short_name": "GPX4U",
            "name": "GPX4U Running Analysis",
            "start_url": "."
        })

@app.route('/robots.txt')
def serve_robots_txt():
    """Serve the robots.txt file."""
    try:
        # First check if file exists in static directory
        static_path = os.path.join('static', 'robots.txt')
        
        if os.path.exists(static_path):
            with open(static_path, 'r') as f:
                content = f.read()
        else:
            # Provide a default robots.txt if file not found
            content = "User-agent: *\nAllow: /"
            
        response = app.response_class(
            response=content,
            status=200,
            mimetype='text/plain'
        )
        
        response.headers['Cache-Control'] = 'public, max-age=31536000'
        return response
        
    except Exception as e:
        print(f"Error serving robots.txt: {str(e)}")
        traceback.print_exc()
        
        # Return a default robots.txt as fallback
        content = "User-agent: *\nAllow: /"
        
        response = app.response_class(
            response=content,
            status=200,
            mimetype='text/plain'
        )
        
        response.headers['Cache-Control'] = 'public, max-age=31536000'
        return response

@app.route('/logo192.png')
def serve_logo192():
    try:
        print("Serving logo192.png")
        search_paths = [
            'static/logo192.png',
            'backend/static/logo192.png',
            os.path.join(os.getcwd(), 'static/logo192.png'),
            os.path.join(os.getcwd(), 'backend/static/logo192.png')
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                print(f"Found logo at: {path}")
                return send_from_directory(os.path.dirname(path), os.path.basename(path), 
                                          mimetype='image/png')
        
        # If logo is not found, generate a simple placeholder logo
        print("Generating placeholder logo")
        from PIL import Image, ImageDraw
        import io
        
        # Create a 192x192 image with blue background
        img = Image.new('RGB', (192, 192), color=(66, 133, 244))
        draw = ImageDraw.Draw(img)
        
        # Draw a white circle
        draw.ellipse((48, 48, 144, 144), fill=(255, 255, 255))
        
        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Create a response with the image
        response = make_response(img_io.getvalue())
        response.headers.set('Content-Type', 'image/png')
        return response
    except Exception as e:
        print(f"Error serving logo192.png: {e}")
        # Return a 204 No Content on error
        return app.response_class(
            response='',
            status=204
        )

@app.route('/logo512.png')
def serve_logo512():
    try:
        print("Serving logo512.png")
        search_paths = [
            'static/logo512.png',
            'backend/static/logo512.png',
            os.path.join(os.getcwd(), 'static/logo512.png'),
            os.path.join(os.getcwd(), 'backend/static/logo512.png')
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                print(f"Found logo at: {path}")
                return send_from_directory(os.path.dirname(path), os.path.basename(path), 
                                          mimetype='image/png')
        
        # If logo is not found, generate a simple placeholder logo
        print("Generating placeholder logo")
        from PIL import Image, ImageDraw
        import io
        
        # Create a 512x512 image with blue background
        img = Image.new('RGB', (512, 512), color=(66, 133, 244))
        draw = ImageDraw.Draw(img)
        
        # Draw a white circle
        draw.ellipse((128, 128, 384, 384), fill=(255, 255, 255))
        
        # Convert to bytes
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Create a response with the image
        response = make_response(img_io.getvalue())
        response.headers.set('Content-Type', 'image/png')
        return response
    except Exception as e:
        print(f"Error serving logo512.png: {e}")
        # Return a 204 No Content on error
        return app.response_class(
            response='',
            status=204
        )

@app.route('/static/js/main.ed081796.js')
def serve_main_js():
    try:
        print("\n=== Serving Main JS ===")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers for JS file
        origin = request.headers.get('Origin', '')
        allowed_origins = ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com", "http://localhost:3000"]
        print(f"Request origin: {origin}")
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/javascript',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in allowed_origins:
            headers['Access-Control-Allow-Origin'] = origin
            print(f"Using origin from request: {origin}")
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            print("Using default origin: https://gpx4u.com")
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        print(f"Final headers: {headers}")
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/js/main.ed081796.js'
        print(f"Checking file path: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/javascript'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                print(f"Successfully created response")
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Main JS file not found: {file_path}")
        return jsonify({"error": "Main JS file not found"}), 404
    except Exception as e:
        print(f"Error serving main JS file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/css/main.454d5194.css')
def serve_main_css():
    try:
        print("\n=== Serving Main CSS ===")
        app_root = os.path.dirname(os.path.abspath(__file__))
        css_dir = os.path.join(app_root, 'static', 'css')
        filename = 'main.454d5194.css'
        
        print(f"App root: {app_root}")
        print(f"CSS directory: {css_dir}")
        print(f"Filename: {filename}")
        print(f"Full path: {os.path.join(css_dir, filename)}")
        print(f"File exists: {os.path.exists(os.path.join(css_dir, filename))}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir(css_dir)}")
        
        origin = request.headers.get('Origin', '')
        print(f"Request origin: {origin}")
        
        headers = {
            'Cache-Control': 'public, max-age=31536000',
            'Access-Control-Allow-Credentials': 'true'
        }
        
        if origin in ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com", "http://localhost:3000"]:
            headers['Access-Control-Allow-Origin'] = origin
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        print(f"Headers before send_from_directory: {headers}")
        
        try:
            response = send_from_directory(
                directory=css_dir,
                path=filename,
                mimetype='text/css',
                as_attachment=False,
                download_name=None,
                conditional=True
            )
            
            for key, value in headers.items():
                response.headers[key] = value
                
            print(f"Response headers: {dict(response.headers)}")
            return response
            
        except Exception as e:
            print(f"Error in send_from_directory: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"Error serving CSS file: {str(e)}"}), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/js/488.7dee82e4.chunk.js')
def serve_chunk_js():
    try:
        print("\n=== Serving Chunk JS ===")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers for JS file
        origin = request.headers.get('Origin', '')
        allowed_origins = ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com", "http://localhost:3000"]
        print(f"Request origin: {origin}")
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/javascript',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in allowed_origins:
            headers['Access-Control-Allow-Origin'] = origin
            print(f"Using origin from request: {origin}")
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            print("Using default origin: https://gpx4u.com")
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        print(f"Final headers: {headers}")
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/js/488.7dee82e4.chunk.js'
        print(f"Checking file path: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/javascript'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                print(f"Successfully created response")
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Chunk JS file not found: {file_path}")
        return jsonify({"error": "Chunk JS file not found"}), 404
    except Exception as e:
        print(f"Error serving chunk JS file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/auth/check', methods=['GET', 'OPTIONS'])
def check_auth():
    print("\n=== Auth Check ===")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Session: {dict(session)}")
    
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            # Get user info to return
            user = db.get_user_by_id(user_id)
            if user:
                response = jsonify({
                    'authenticated': True,
                    'user_id': user['id'],
                    'username': user['username'],
                    'email': user.get('email', '')
                })
            else:
                # Session exists but user not found - clear session
                session.clear()
                response = jsonify({
                    'authenticated': False,
                    'user_id': None
                })
        else:
            # If we get here, user is not authenticated
            response = jsonify({
                'authenticated': False,
                'user_id': None
            })
            
        # Set explicit CORS headers
        origin = request.headers.get('Origin', '')
        print(f"Origin header: {origin}")
        
        # Special handling for production URLs
        if origin and 'herokuapp.com' in origin:
            print(f"Setting Access-Control-Allow-Origin to match herokuapp origin: {origin}")
            response.headers['Access-Control-Allow-Origin'] = origin
        elif origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            print(f"Setting Access-Control-Allow-Origin from allowed origins: {origin}")
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            print(f"Using default Access-Control-Allow-Origin: https://gpx4u.com")
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        print(f"Response headers: {dict(response.headers)}")
        return response
        
    except Exception as e:
        print(f"Auth check error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({
            'authenticated': False,
            'error': str(e),
            'user_id': None
        })
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin and 'herokuapp.com' in origin:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        elif origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500

@app.route('/auth/login', methods=['POST', 'OPTIONS'])
def login():
    print("\n=== Login Attempt ===")
    try:
        data = request.json
        print(f"Login attempt for: {data.get('username', 'unknown')}")
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            print("Missing username or password")
            error_response = jsonify({'error': 'Missing username or password'})
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                error_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 400
            
        # Check credentials
        user_id = db.verify_user(username, password)
        if user_id:
            print(f"Login successful for user: {username}")
            session['user_id'] = user_id
            session.permanent = True
            
            # Get additional user details
            user = db.get_user_by_id(user_id)
            
            success_response = jsonify({
                'message': 'Login successful',
                'user_id': user_id,
                'username': username
            })
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                success_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                success_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            success_response.headers['Access-Control-Allow-Credentials'] = 'true'
            success_response.headers['Vary'] = 'Origin'
            return success_response
        else:
            print(f"Invalid login credentials for: {username}")
            error_response = jsonify({'error': 'Invalid credentials'})
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                error_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500

@app.route('/auth/logout', methods=['POST', 'OPTIONS'])
def logout():
    print("\n=== Logout ===")
    try:
        session.clear()
        response = jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
        # Set CORS headers 
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        return response
    except Exception as e:
        print(f"Logout error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({
            'success': False,
            'error': str(e)
        })
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500

@app.route('/auth/register', methods=['POST', 'OPTIONS'])
def register():
    print("\n=== Register User ===")
    try:
        data = request.json
        print(f"Registration attempt for: {data.get('username', 'unknown')}")
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password or not email:
            print("Missing required registration fields")
            error_response = jsonify({'error': 'Missing required fields'})
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                error_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 400
            
        # Check if user already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            print(f"Username already exists: {username}")
            error_response = jsonify({'error': 'Username already exists'})
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                error_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 409
            
        # Register the new user
        user_id = db.register_user(username, password, email)
        if user_id:
            print(f"Registration successful for user: {username}")
            session['user_id'] = user_id
            session.permanent = True
            
            # Create default profile for the user
            db.save_profile(
                user_id=user_id,
                age=30,  # Default values
                resting_hr=60,
                weight=70,
                gender=0
            )
            
            success_response = jsonify({
                'message': 'Registration successful',
                'user_id': user_id,
                'username': username
            })
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                success_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                success_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            success_response.headers['Access-Control-Allow-Credentials'] = 'true'
            success_response.headers['Vary'] = 'Origin'
            return success_response
        else:
            print(f"Failed to register user: {username}")
            error_response = jsonify({'error': 'Registration failed'})
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                error_response.headers['Access-Control-Allow-Origin'] = origin
            else:
                error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 500
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500

@app.route('/static/js/main.ed081796.js.map')
def serve_main_js_map():
    try:
        print("\n=== Serving Main JS Map ===")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers
        origin = request.headers.get('Origin', '')
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            headers['Access-Control-Allow-Origin'] = origin
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        
        # First check local paths
        local_paths = [
            os.path.join('static/js', 'main.39b03b12.js.map'),
            os.path.join('backend/static/js', 'main.39b03b12.js.map'),
            os.path.join('build/static/js', 'main.39b03b12.js.map')
        ]
        
        for path in local_paths:
            if os.path.exists(path):
                print(f"Found file at local path: {path}")
                dir_path, file_name = os.path.split(path)
                return send_from_directory(dir_path, file_name, headers=headers)
                
        # Then try Heroku path as fallback
        file_path = '/app/backend/static/js/main.39b03b12.js.map'
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/json'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Main JS map file not found: {file_path}")
        return jsonify({"error": "Main JS map file not found"}), 404
    except Exception as e:
        print(f"Error serving main JS map file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/css/main.454d5194.css.map')
def serve_main_css_map():
    try:
        print("\n=== Serving Main CSS Map ===")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers
        origin = request.headers.get('Origin', '')
        allowed_origins = ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com", "http://localhost:3000"]
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in allowed_origins:
            headers['Access-Control-Allow-Origin'] = origin
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/css/main.454d5194.css.map'
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/json'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Main CSS map file not found: {file_path}")
        return jsonify({"error": "Main CSS map file not found"}), 404
    except Exception as e:
        print(f"Error serving main CSS map file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/js/488.7dee82e4.chunk.js.map')
def serve_chunk_js_map():
    try:
        print("\n=== Serving Chunk JS Map ===")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers
        origin = request.headers.get('Origin', '')
        allowed_origins = ["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com", "http://localhost:3000"]
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in allowed_origins:
            headers['Access-Control-Allow-Origin'] = origin
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/js/488.7dee82e4.chunk.js.map'
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/json'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Chunk JS map file not found: {file_path}")
        return jsonify({"error": "Chunk JS map file not found"}), 404
    except Exception as e:
        print(f"Error serving chunk JS map file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/js/main.39b03b12.js')
def serve_main_js_latest():
    try:
        print("\n=== Serving Main JS ===")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers for JS file
        origin = request.headers.get('Origin', '')
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/javascript',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            headers['Access-Control-Allow-Origin'] = origin
            print(f"Using origin from request: {origin}")
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            print("Using default origin: https://gpx4u.com")
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        print(f"Final headers: {headers}")
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/js/main.39b03b12.js'
        print(f"Checking file path: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/javascript'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                print(f"Successfully created response")
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        # If Heroku path doesn't exist, try local directories
        local_paths = [
            os.path.join('static/js', 'main.39b03b12.js'),
            os.path.join('backend/static/js', 'main.39b03b12.js'),
            os.path.join('build/static/js', 'main.39b03b12.js')
        ]
        
        for path in local_paths:
            if os.path.exists(path):
                print(f"Found file at local path: {path}")
                dir_path, file_name = os.path.split(path)
                return send_from_directory(dir_path, file_name, headers=headers)
                
        print(f"Main JS file not found in any location")
        return jsonify({"error": "Main JS file not found"}), 404
    except Exception as e:
        print(f"Error serving main JS file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/js/main.4908f7be.js')
def serve_main_js_20250327():
    try:
        print("\n=== Serving Main JS ===")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers for JS file
        origin = request.headers.get('Origin', '')
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/javascript',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            headers['Access-Control-Allow-Origin'] = origin
            print(f"Using origin from request: {origin}")
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            print("Using default origin: https://gpx4u.com")
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        print(f"Final headers: {headers}")
        
        # Use the correct Heroku path
        file_path = '/app/backend/static/js/main.4908f7be.js'
        print(f"Checking file path: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/javascript'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                print(f"Successfully created response")
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        # If Heroku path doesn't exist, try local directories
        local_paths = [
            os.path.join('static/js', 'main.4908f7be.js'),
            os.path.join('backend/static/js', 'main.4908f7be.js'),
            os.path.join('build/static/js', 'main.4908f7be.js')
        ]
        
        for path in local_paths:
            if os.path.exists(path):
                print(f"Found file at local path: {path}")
                dir_path, file_name = os.path.split(path)
                return send_from_directory(dir_path, file_name, headers=headers)
                
        print(f"Main JS file not found in any location")
        return jsonify({"error": "Main JS file not found"}), 404
    except Exception as e:
        print(f"Error serving main JS file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/static/js/main.4908f7be.js.map')
def serve_main_js_map_20250327():
    try:
        print("\n=== Serving Main JS Map ===")
        print(f"Current working directory: {os.getcwd()}")
        
        # Set CORS headers
        origin = request.headers.get('Origin', '')
        
        # Set proper CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=31536000',
            'Vary': 'Origin'
        }
        
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            headers['Access-Control-Allow-Origin'] = origin
        else:
            headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        headers['Access-Control-Allow-Credentials'] = 'true'
        
        # First check local paths
        local_paths = [
            os.path.join('static/js', 'main.4908f7be.js.map'),
            os.path.join('backend/static/js', 'main.4908f7be.js.map'),
            os.path.join('build/static/js', 'main.4908f7be.js.map')
        ]
        
        for path in local_paths:
            if os.path.exists(path):
                print(f"Found file at local path: {path}")
                dir_path, file_name = os.path.split(path)
                return send_from_directory(dir_path, file_name, headers=headers)
                
        # Then try Heroku path as fallback
        file_path = '/app/backend/static/js/main.4908f7be.js.map'
        
        if os.path.exists(file_path):
            print(f"Found file at: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                response = app.response_class(
                    response=content,
                    status=200,
                    mimetype='application/json'
                )
                for key, value in headers.items():
                    response.headers[key] = value
                return response
            except Exception as inner_e:
                print(f"Error creating response: {str(inner_e)}")
                traceback.print_exc()
                raise
            
        print(f"Main JS map file not found: {file_path}")
        return jsonify({"error": "Main JS map file not found"}), 404
    except Exception as e:
        print(f"Error serving main JS map file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/runs', methods=['GET'])
@login_required
def get_runs():
    try:
        print("\n=== Getting Run History ===")
        print(f"User ID: {session['user_id']}")
        
        # Force database reset to ensure a clean connection
        db.conn = None
        db.cursor = None
        db.connect()
        print("Database connection reset to ensure a fresh connection")
        
        # Get all runs for the user
        try:
            runs = db.get_all_runs(session['user_id'])
            print(f"Found {len(runs)} runs in database")
            
            # Debug: Print the first run if available
            if runs and len(runs) > 0:
                first_run = runs[0]
                print(f"First run ID: {first_run.get('id')}")
                print(f"First run date: {first_run.get('date')}")
            
            formatted_runs = []
            for run in runs:
                try:
                    # Process each run
                    run_id = run.get('id')
                    run_date = run.get('date')
                    run_distance = run.get('total_distance')
                    
                    # For data field, convert from JSON string if needed
                    run_data = None
                    if 'data' in run and run['data']:
                        if isinstance(run['data'], str):
                            try:
                                run_data = json.loads(run['data'])
                            except:
                                print(f"Failed to parse run data JSON for run ID {run_id}")
                                run_data = {}
                        else:
                            run_data = run['data']
                    
                    # Create a formatted representation
                    formatted_run = {
                        'id': run_id,
                        'date': run_date,
                        'distance': run_distance or 0,
                        'data': run_data
                    }
                    formatted_runs.append(formatted_run)
                except Exception as run_error:
                    print(f"Error processing run {run.get('id', 'unknown')}: {str(run_error)}")
                    traceback.print_exc()
                    
            # Return the formatted runs
            response = jsonify(formatted_runs)
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'
            
            return response
            
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            traceback.print_exc()
            
            # Try once more with a fresh connection
            try:
                print("Retrying with a fresh database connection...")
                db.conn = None
                db.cursor = None
                db.connect()
                
                runs = db.get_all_runs(session['user_id'])
                print(f"Retry succeeded! Found {len(runs)} runs in database")
                
                formatted_runs = []
                for run in runs:
                    try:
                        # Process each run
                        run_id = run.get('id')
                        run_date = run.get('date')
                        run_distance = run.get('total_distance')
                        
                        # For data field, convert from JSON string if needed
                        run_data = None
                        if 'data' in run and run['data']:
                            if isinstance(run['data'], str):
                                try:
                                    run_data = json.loads(run['data'])
                                except:
                                    run_data = {}
                            else:
                                run_data = run['data']
                        
                        # Create a formatted representation
                        formatted_run = {
                            'id': run_id,
                            'date': run_date,
                            'distance': run_distance or 0,
                            'data': run_data
                        }
                        formatted_runs.append(formatted_run)
                    except Exception as inner_run_error:
                        print(f"Error processing run after retry: {str(inner_run_error)}")
                
                response = jsonify(formatted_runs)
                
                # Set CORS headers
                origin = request.headers.get('Origin', '')
                if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
                    response.headers['Access-Control-Allow-Origin'] = origin
                else:
                    response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
                    
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['Vary'] = 'Origin'
                
                return response
            except Exception as retry_error:
                print(f"Retry also failed: {str(retry_error)}")
                traceback.print_exc()
                raise db_error  # Re-raise the original error
            
    except Exception as e:
        print(f"Error getting runs: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({
            'error': str(e),
            'message': 'Failed to retrieve run history'
        })
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        
        return error_response, 500

@app.route('/db-test', methods=['GET'])
def test_database():
    try:
        print("\n=== Testing Database Connection ===")
        
        # Get basic system info
        current_dir = os.getcwd()
        
        # Force database reconnection
        db.conn = None
        db.cursor = None
        db.check_connection()
        
        # Check database type
        is_postgres = isinstance(db.conn, psycopg2.extensions.connection)
        db_type = "PostgreSQL" if is_postgres else "SQLite"
        
        # Test tables
        tables_info = {}
        if is_postgres:
            # PostgreSQL tests
            db.cursor.execute("SELECT current_database(), current_user")
            db_info = db.cursor.fetchone()
            db_name = db_info[0]
            db_user = db_info[1]
            
            # Get table info
            db.cursor.execute("""
                SELECT table_name, 
                       (SELECT count(*) FROM information_schema.columns WHERE table_name=t.table_name) AS column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = db.cursor.fetchall()
            for table in tables:
                table_name = table[0]
                # Get row count
                db.cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                row_count = db.cursor.fetchone()[0]
                tables_info[table_name] = {
                    "column_count": table[1],
                    "row_count": row_count
                }
        else:
            # SQLite tests
            db.cursor.execute("SELECT sqlite_version()")
            db_info = db.cursor.fetchone()
            db_name = db.db_name  # Fixed: using db.db_name instead of self.db_name
            db_user = "sqlite"
            
            # Get table info
            db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in db.cursor.fetchall()]
            for table_name in tables:
                # Get column count
                db.cursor.execute(f"PRAGMA table_info({table_name})")
                column_count = len(db.cursor.fetchall())
                # Get row count
                db.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = db.cursor.fetchone()[0]
                tables_info[table_name] = {
                    "column_count": column_count,
                    "row_count": row_count
                }
                
        # Get Environment info
        environment_info = {
            "DATABASE_URL": "exists" if os.environ.get("DATABASE_URL") else "not found",
            "FLASK_ENV": os.environ.get("FLASK_ENV", "not set"),
            "DYNO": os.environ.get("DYNO", "not set"),
            "CURRENT_DIRECTORY": current_dir
        }
        
        # Try to create a test record and read it back
        test_data = {
            "test_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "test_value": "Database connectivity test"
        }
        if is_postgres:
            db.cursor.execute(
                "CREATE TABLE IF NOT EXISTS db_tests (id SERIAL PRIMARY KEY, test_time TIMESTAMP, test_data JSONB)",
            )
            db.cursor.execute(
                "INSERT INTO db_tests (test_time, test_data) VALUES (%s, %s) RETURNING id",
                (datetime.now(), json.dumps(test_data))
            )
            test_id = db.cursor.fetchone()[0]
            db.conn.commit()
            
            db.cursor.execute("SELECT * FROM db_tests WHERE id = %s", (test_id,))
            test_result = db.cursor.fetchone()
            test_retrieved = bool(test_result)
        else:
            db.cursor.execute(
                "CREATE TABLE IF NOT EXISTS db_tests (id INTEGER PRIMARY KEY, test_time TEXT, test_data TEXT)"
            )
            db.cursor.execute(
                "INSERT INTO db_tests (test_time, test_data) VALUES (?, ?)",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), json.dumps(test_data))
            )
            test_id = db.cursor.lastrowid
            db.conn.commit()
            
            db.cursor.execute("SELECT * FROM db_tests WHERE id = ?", (test_id,))
            test_result = db.cursor.fetchone()
            test_retrieved = bool(test_result)
            
        return jsonify({
            'status': 'Database connection test successful',
            'database_type': db_type,
            'database_name': db_name,
            'database_user': db_user,
            'tables': tables_info,
            'environment': environment_info,
            'test_write_successful': test_id is not None,
            'test_read_successful': test_retrieved,
            'connection_thread_id': db.conn_thread_id
        }), 200
    except Exception as e:
        error_detail = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        print("Database test error:", error_detail)
        return jsonify({
            'status': 'Database connection test failed',
            'error': str(e),
            'error_detail': error_detail
        }), 500

@app.route('/db-test-detail', methods=['GET'])
def test_database_detail():
    try:
        print("\n===== Running Detailed Database Tests =====")
        
        # Import the test function from our new script
        from db_test import test_database_connection
        
        # Run all the tests
        results = test_database_connection()
        
        # Add HTTP headers for CORS
        response = jsonify(results)
        
        # Set CORS headers
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
        return response
    except Exception as e:
        print(f"Error running detailed database tests: {str(e)}")
        traceback.print_exc()
        
        error_response = jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS:
            error_response.headers['Access-Control-Allow-Origin'] = origin
        else:
            error_response.headers['Access-Control-Allow-Origin'] = 'https://gpx4u.com'
            
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        
        return error_response, 500

@app.route('/api/diagnostics', methods=['GET'])
def diagnostics():
    """Diagnostic endpoint to help troubleshoot static file serving issues."""
    current_dir = os.getcwd()
    
    # Check static directories
    static_paths = [
        'static',
        'static/js',
        'static/css',
        'backend/static',
        'backend/static/js',
        'backend/static/css',
        'templates'
    ]
    
    # Check existence of directories
    dir_exists = {path: os.path.isdir(os.path.join(current_dir, path)) for path in static_paths}
    
    # List contents of directories that exist
    dir_contents = {
        path: os.listdir(os.path.join(current_dir, path)) 
        for path in static_paths 
        if os.path.isdir(os.path.join(current_dir, path))
    }
    
    # Check index.html
    index_path = os.path.join(current_dir, 'templates', 'index.html')
    index_exists = os.path.isfile(index_path)
    index_size = os.path.getsize(index_path) if index_exists else 0
    
    # Get Flask static folder config
    static_folder = app.static_folder
    static_url_path = app.static_url_path
    
    return jsonify({
        'current_dir': current_dir,
        'dir_exists': dir_exists,
        'dir_contents': dir_contents,
        'index_exists': index_exists, 
        'index_size': index_size,
        'flask_config': {
            'static_folder': static_folder,
            'static_url_path': static_url_path
        },
        'env_vars': {
            'FLASK_ENV': os.environ.get('FLASK_ENV', 'not set'),
            'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', 'not set'),
            'PORT': os.environ.get('PORT', 'not set'),
            'RENDER_SERVICE_NAME': os.environ.get('RENDER_SERVICE_NAME', 'not set'),
            'RENDER_EXTERNAL_URL': os.environ.get('RENDER_EXTERNAL_URL', 'not set')
        }
    })

@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(e):
    """Handle 404 and 500 errors by returning a friendly HTML page"""
    print(f"Error handler triggered: {type(e).__name__} - {str(e)}")
    
    # Construct helpful error page
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>GPX4U - Error</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .app {{ max-width: 960px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4285f4; color: white; padding: 20px; text-align: center; margin-bottom: 30px; border-radius: 5px; }}
            h1 {{ margin: 0; }}
            p {{ line-height: 1.6; color: #333; }}
            .container {{ background-color: white; padding: 30px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .error {{ background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
            .links a {{ display: inline-block; padding: 10px 15px; background-color: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="app">
            <div class="header">
                <h1>GPX4U Running Analysis</h1>
            </div>
            <div class="container">
                <h2>Oops! Something went wrong</h2>
                <div class="error">
                    <strong>Error {e.code if hasattr(e, 'code') else 500}:</strong> {str(e)}
                </div>
                <p>The server encountered an issue while processing your request. This might be due to:</p>
                <ul>
                    <li>A missing file or resource</li>
                    <li>Temporary server issue</li>
                    <li>Configuration problem</li>
                </ul>
                <div class="links">
                    <a href="/">Return to Home Page</a>
                    <a href="/api/diagnostics">System Diagnostics</a>
                    <a href="/health">API Health Check</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create response
    response = app.response_class(
        response=html,
        status=e.code if hasattr(e, 'code') else 500,
        mimetype='text/html'
    )
    
    return response

if __name__ == '__main__':
    # Get port from environment variable (default to 5001 if not set)
    port = int(os.environ.get('PORT', 5001))
    
    # Determine if we're in production based on environment variable
    is_production = os.environ.get('RENDER', False) or os.environ.get('FLASK_ENV', '') == 'production'
    
    # Use appropriate settings based on environment
    if is_production:
        print(f"Starting production server on http://0.0.0.0:{port}")
        app.run(
            debug=False,
            host='0.0.0.0',
            port=port,
            ssl_context=None
        )
    else:
        print(f"Starting development server on http://localhost:{port}")
        app.run(
            debug=True,
            host='localhost',
            port=port,
            ssl_context=None
        ) 