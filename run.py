# run.py

from app import create_app
from app.config import Config  # Add this line
from dotenv import load_dotenv
import os

load_dotenv()  # This will load variables from .env into the environment

app = create_app()
app.config.from_object(Config)

if __name__ == '__main__':
    app.run(port=5001)