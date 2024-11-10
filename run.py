# run.py
from app import create_app
from dotenv import load_dotenv
from app.config import get_config
import os

# Load environment variables from .env file for local development
load_dotenv()

# Initialize app with the correct configuration
app = create_app(get_config())

if __name__ == "__main__":
    # Get the PORT from the configuration
    port = app.config["PORT"]
    app.run(host="0.0.0.0", port=port)