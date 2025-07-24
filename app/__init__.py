# app/__init__.py
from flask import Flask, render_template_string
from flask_cors import CORS
from app.config import get_config
from app.extensions import db
from app.routes import api  # Import the Api instance with namespaces

def create_app(config_class=None):
    app = Flask(__name__)

    # Configure CORS to allow requests from any origin for specific routes
    # and to handle the necessary headers and methods.
    CORS(app, resources={
        r"/stations/*": {
            "origins": "*",
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        },
        r"/trains/*": {
            "origins": "*",
            "methods": ["GET", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        },
        r"/reports/*": {
            "origins": "*",
            "methods": ["POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })

    app.config.from_object(config_class or get_config())

    @app.route("/redoc")
    def redoc():
        redoc_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Train Tracking API Docs</title>
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
        </head>
        <body>
            <redoc spec-url="/swagger.json"></redoc>
        </body>
        </html>
        """
        return render_template_string(redoc_html)

    # Initialize extensions
    db.init_app(app)
    api.init_app(app)

    return app