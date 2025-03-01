from flask import Blueprint, request, jsonify, session
import traceback
from backend.app.database import RunDatabase
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth_bp', __name__)
db = RunDatabase()

@auth_bp.route('/auth/register', methods=['POST'])
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


@auth_bp.route('/auth/login', methods=['POST'])
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


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})


@auth_bp.route('/auth/check', methods=['GET'])
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


@auth_bp.route('/auth/change-password', methods=['POST'])
def change_password():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401

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