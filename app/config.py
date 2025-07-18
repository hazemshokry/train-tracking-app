# app/config.py
import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class LocalConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql://root:hazemshokry@localhost:3306/db1")
    PORT = int(os.getenv("PORT", 5001))

class CloudRunConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql://root:hazemshokry@34.55.195.124:3306/db1")
    PORT = int(os.getenv("PORT", 8080))

def get_config():
    # Use LocalConfig for local development, otherwise CloudRunConfig
    return LocalConfig if os.getenv("FLASK_ENV") == "development" else CloudRunConfig