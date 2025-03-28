# This file can be empty, it just marks the directory as a Python package

from flask import Flask
from flask_session import Session
from flask_cors import CORS
import os
import secrets

def create_app():
    app = Flask(__name__)
    
    # Force production mode for Render deployment
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Configure CORS
    CORS(app,
        origins=["https://gpx4u.com", "http://gpx4u.com", "https://gpx4u-0460cd678569.herokuapp.com",
                "https://gpx4u.onrender.com", "https://*.onrender.com", "*"],
        methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True
    )
    
    # Configure session
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SESSION_COOKIE_NAME='running_session'  # Custom session cookie name
    )
    
    # Generate a secure random key
    app.secret_key = secrets.token_hex(32)
    
    Session(app)
    
    # Register blueprints
    from .routes.runs import runs_bp
    from .routes.auth import auth_bp
    from .routes.profile import profile_bp
    from .routes.healthcheck import health_bp
    
    app.register_blueprint(runs_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(health_bp)
    
    # Add root route
    @app.route('/api')
    def api_info():
        render_external_url = os.environ.get('RENDER_EXTERNAL_URL', 'unknown')
        service_name = os.environ.get('RENDER_SERVICE_NAME', 'gpx4u')
        return {
            'status': 'ok', 
            'message': 'GPX4U API server is running', 
            'version': '1.0.0',
            'service_info': {
                'name': service_name,
                'public_url': render_external_url,
                'environment': os.environ.get('FLASK_ENV', 'production')
            },
            'endpoints': [
                f'{render_external_url}/health',
                f'{render_external_url}/server-test',
                f'{render_external_url}/runs',
                f'{render_external_url}/profile',
                f'{render_external_url}/auth/login',
                f'{render_external_url}/auth/register',
                f'{render_external_url}/auth/logout',
                f'{render_external_url}/auth/check',
                f'{render_external_url}/analyze'
            ]
        }
    
    return app

app = create_app()
