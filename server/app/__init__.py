import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS


socketio = SocketIO()

def create_app(debug=True):
    """Create an application."""
    app = Flask(__name__)
    cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '*')
    CORS(app, origins="*")
    app.debug = debug
    app.config['SECRET_KEY'] = 'gjr39dkjn344_!67#'

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    socketio.init_app(app, cors_allowed_origins='*')

    return app