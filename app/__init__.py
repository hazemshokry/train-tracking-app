from flask import Flask, render_template_string
from app.config import Config
from app.extensions import db
from app.routes import api  # Import the Api instance with namespaces

def create_app(config_class=Config):
    app = Flask(__name__)
    
    app.config.from_object(config_class)

    @app.route("/redoc")
    def redoc():
        redoc_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Train Tracking API Docs</title>
            <!-- Embed the ReDoc library -->
                <redoc spec-url="/swagger.json"></redoc>
                <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"> </script>        </head>
        <body>
            <!-- Update with the direct path to your Swagger JSON -->
            <redoc spec-url="/swagger.json"></redoc>
        </body>
        </html>
        """
        return render_template_string(redoc_html)
        # Initialize extensions

    db.init_app(app)

    # Initialize API with Swagger UI
    api.init_app(app)

    return app