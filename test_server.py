from flask import Flask, jsonify, request, session
from flask_cors import CORS
import secrets
from backend.app.database import RunDatabase
import traceback

app = Flask(__name__)

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

# Allow all origins for testing
CORS(app, 
    supports_credentials=True, 
    origins="*",
    methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Cache-Control"],
    expose_headers=["Content-Type", "Authorization", "Cache-Control"]
)

# Initialize database
db = RunDatabase()

@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'CORS test server running'
    })

@app.route('/auth/check')
def auth_check():
    print("\n=== Auth Check ===")
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
                    'username': user['username']
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
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
        
        return response
        
    except Exception as e:
        print(f"Auth check error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({
            'authenticated': False,
            'error': str(e)
        })
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '')
        error_response.headers['Access-Control-Allow-Origin'] = origin
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500
        
@app.route('/auth/login', methods=['POST'])
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
            error_response.headers['Access-Control-Allow-Origin'] = origin
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 400
            
        # Check credentials
        user_id = db.verify_user(username, password)
        if user_id:
            print(f"Login successful for user: {username}")
            session['user_id'] = user_id
            session.permanent = True
            
            success_response = jsonify({
                'message': 'Login successful',
                'user_id': user_id,
                'username': username
            })
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            success_response.headers['Access-Control-Allow-Origin'] = origin
            success_response.headers['Access-Control-Allow-Credentials'] = 'true'
            success_response.headers['Vary'] = 'Origin'
            return success_response
        else:
            print(f"Invalid login credentials for: {username}")
            error_response = jsonify({'error': 'Invalid credentials'})
            
            # Set CORS headers
            origin = request.headers.get('Origin', '')
            error_response.headers['Access-Control-Allow-Origin'] = origin
            error_response.headers['Access-Control-Allow-Credentials'] = 'true'
            error_response.headers['Vary'] = 'Origin'
            return error_response, 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        
        # Set CORS headers even on error
        origin = request.headers.get('Origin', '') 
        error_response.headers['Access-Control-Allow-Origin'] = origin
        error_response.headers['Access-Control-Allow-Credentials'] = 'true'
        error_response.headers['Vary'] = 'Origin'
        return error_response, 500

if __name__ == '__main__':
    print("Starting test server on http://localhost:5001")
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001
    ) 