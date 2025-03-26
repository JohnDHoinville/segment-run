# This file can be empty, it just marks the directory as a Python package

from flask import Flask
from flask_session import Session
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configure session
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)
    
    # Register blueprints
    from .routes import runs
    app.register_blueprint(runs.bp)
    
    return app

app = create_app()
