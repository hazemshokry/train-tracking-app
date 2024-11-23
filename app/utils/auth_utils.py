# app/utils/auth_util.py

from functools import wraps
from flask import request
import jwt
import os
import pyotp
import base64
import hashlib
import hmac
from datetime import datetime
from app.extensions import db

# Secret key for JWT
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

def generate_totp_secret(phone_number):
    """Generate a TOTP secret based on the phone number and SECRET_KEY."""
    key = SECRET_KEY.encode()
    msg = phone_number.encode()
    hmac_digest = hmac.new(key, msg, hashlib.sha256).digest()
    secret = base64.b32encode(hmac_digest).decode('utf-8')
    return secret

def token_required(f):
    """Decorator to ensure that the user has a valid access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.models.user import User  # Import here to avoid circular imports
        token = None
        # Check for token in header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
        if not token:
            return {'message': 'Token is missing'}, 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return {'message': 'User not found'}, 401
            request.current_user = current_user
        except jwt.ExpiredSignatureError:
            return {'message': 'Token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Invalid token'}, 401
        return f(*args, **kwargs)
    return decorated