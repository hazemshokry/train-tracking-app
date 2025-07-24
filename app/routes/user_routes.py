# app/routes/user_routes.py

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.device_token import DeviceToken # Import the new model
from app.extensions import db
from datetime import datetime, timedelta
import jwt
import os
import uuid
import pyotp

# Import the authentication utilities
from app.utils.auth_utils import generate_totp_secret, token_required


api = Namespace(
    'users',
    description='User related operations',
    security='BearerAuth',
    authorizations={
        'BearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter your token directly or with Bearer prefix, e.g., **Bearer &lt;token&gt;** or **&lt;token&gt;**'
        }
    }
)

# Secret key for JWT
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Serializer models
user_model = api.model('User', {
    'id': fields.String(readOnly=True, description='Unique identifier of the user'),
    'username': fields.String(description='Username'),
    'email': fields.String(description='Email address'),
    'phone_number': fields.String(description='Phone number'),
    'is_active': fields.Boolean(description='Active status'),
    'date_joined': fields.DateTime(description='Date joined'),
    'last_login': fields.DateTime(description='Last login time'),
    'reliability_score': fields.Float(description='User reliability score'),
})

token_model = api.model('Tokens', {
    'access_token': fields.String(description='Access token'),
    'refresh_token': fields.String(description='Refresh token'),
})

temp_token_model = api.model('TempToken', {
    'temp_token': fields.String(description='Temporary token for registration'),
})

# New response model for registration to include tokens and user data
registration_response_model = api.model('RegistrationResponse', {
    'access_token': fields.String(description='Access token for the new user'),
    'refresh_token': fields.String(description='Refresh token for the new user'),
    'user': fields.Nested(user_model)
})


# Authentication routes
@api.route('/login/send_otp')
class LoginSendOTP(Resource):
    @api.expect(api.model('PhoneNumberInput', {'phone_number': fields.String(required=True)}))
    def post(self):
        """Send OTP to the provided phone number regardless of registration status."""
        data = api.payload
        phone_number = data.get('phone_number')

        # Generate OTP
        totp_secret = generate_totp_secret(phone_number)
        totp = pyotp.TOTP(totp_secret)
        otp_code = totp.now()

        # Send OTP to user's phone number (simulate or integrate with SMS service)
        print(f"Sending OTP {otp_code} to phone number {phone_number}")

        return {'message': f'OTP {otp_code} sent successfully'}, 200

@api.route('/login/validate_otp')
class LoginValidateOTP(Resource):
    @api.expect(api.model('OTPValidation', {
        'phone_number': fields.String(required=True),
        'otp_code': fields.String(required=True),
        'device_token': fields.String(description='Firebase device token')
    }))
    @api.response(200, 'Login successful', model=token_model)
    @api.response(201, 'Proceed to registration', model=temp_token_model)
    def post(self):
        """Validate OTP and log in or provide temporary token for registration."""
        data = api.payload
        phone_number = data.get('phone_number').strip()
        otp_code = data.get('otp_code').strip()
        device_token = data.get('device_token')


        # Validate OTP
        totp_secret = generate_totp_secret(phone_number)
        totp = pyotp.TOTP(totp_secret)
        
        # Uncomment the following lines for production to enforce OTP validation
        # if not totp.verify(otp_code, valid_window=1):
        #     return {'message': 'Invalid or expired OTP code'}, 400

        user = User.query.filter_by(phone_number=phone_number).first()

        if user:
            # User exists, proceed to login
            # Generate access token
            access_token = jwt.encode({
                'user_id': user.id,
                'exp': datetime.utcnow() + timedelta(minutes=15)
            }, SECRET_KEY, algorithm='HS256')

            # Generate a new refresh token
            refresh_token_str = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(days=7)

            # Update the refresh token in the database
            existing_refresh_token = RefreshToken.query.filter_by(user_id=user.id).first()
            if existing_refresh_token:
                # Update existing token
                existing_refresh_token.token = refresh_token_str
                existing_refresh_token.expires_at = expires_at
            else:
                # Create a new refresh token record if none exists
                refresh_token = RefreshToken(
                    token=refresh_token_str,
                    user_id=user.id,
                    expires_at=expires_at
                )
                db.session.add(refresh_token)

            user.last_login = datetime.utcnow()
            
            # Save the device token to the new table
            if device_token:
                existing_device_token = DeviceToken.query.filter_by(token=device_token).first()
                if not existing_device_token:
                    new_device_token = DeviceToken(user_id=user.id, token=device_token)
                    db.session.add(new_device_token)
            
            db.session.commit()

            return {
                'access_token': access_token,
                'refresh_token': refresh_token_str,
                'needs_registration': "false"
            }, 200
        else:
            # User does not exist, provide a temporary token for registration
            temp_token = jwt.encode({
                'phone_number': phone_number,
                'exp': datetime.utcnow() + timedelta(minutes=15)
            }, SECRET_KEY, algorithm='HS256')

            return {
                'temp_token': temp_token,
                'needs_registration': "true"
            }, 201

@api.route('/refresh_token')
class RefreshTokenResource(Resource):
    @api.expect(api.model('RefreshTokenInput', {'refresh_token': fields.String(required=True)}))
    @api.marshal_with(token_model)
    def post(self):
        data = api.payload
        refresh_token_str = data.get('refresh_token')
        refresh_token = RefreshToken.query.filter_by(token=refresh_token_str).first()

        if not refresh_token:
            return {'message': 'Invalid refresh token'}, 401

        if datetime.utcnow() > refresh_token.expires_at:
            db.session.delete(refresh_token)
            db.session.commit()
            return {'message': 'Refresh token has expired'}, 401

        user = refresh_token.user

        # Generate new access token
        access_token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes=15)
        }, SECRET_KEY, algorithm='HS256')

        # Optionally, generate a new refresh token
        new_refresh_token_str = str(uuid.uuid4())
        refresh_token.token = new_refresh_token_str
        refresh_token.expires_at = datetime.utcnow() + timedelta(days=7)
        db.session.commit()

        return {
            'access_token': access_token,
            'refresh_token': new_refresh_token_str
        }, 200

@api.route('/complete_registration')
class CompleteRegistration(Resource):
    @api.expect(api.model('UserRegistration', {
        'username': fields.String(required=True, description='Username'),
        'email': fields.String(required=True, description='Email address'),
        'device_token': fields.String(description='Firebase device token')
    }))
    @api.doc(security='BearerAuth')
    @api.marshal_with(registration_response_model, code=201)
    def post(self):
        """Complete registration and return user object with tokens."""
        # Get temp_token from headers
        auth_header = request.headers.get('Authorization')
        print(f"Authorization Header: {auth_header}")
        if not auth_header:
            return {'message': 'Temporary token is missing'}, 401

        # Extract the token, handling both with and without 'Bearer ' prefix
        parts = auth_header.strip().split()

        if len(parts) == 1:
            temp_token = parts[0]
        elif len(parts) == 2 and parts[0].lower() == 'bearer':
            temp_token = parts[1]
        else:
            return {'message': 'Invalid Authorization header format'}, 401

        try:
            data_token = jwt.decode(temp_token, SECRET_KEY, algorithms=['HS256'])
            phone_number = data_token.get('phone_number')
        except jwt.ExpiredSignatureError:
            return {'message': 'Temporary token has expired'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Invalid temporary token'}, 401

        data = api.payload
        username = data.get('username')
        email = data.get('email')
        device_token = data.get('device_token')

        # Create new user
        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
            date_joined=datetime.utcnow(),
        )
        db.session.add(new_user)
        db.session.commit()

        # Generate access token for the new user
        access_token = jwt.encode({
            'user_id': new_user.id,
            'exp': datetime.utcnow() + timedelta(minutes=15)
        }, SECRET_KEY, algorithm='HS256')

        # Generate refresh token for the user
        refresh_token_str = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        refresh_token = RefreshToken(
            token=refresh_token_str,
            user_id=new_user.id,
            expires_at=expires_at
        )
        db.session.add(refresh_token)
        
        # Save the device token to the new table
        if device_token:
            new_device_token = DeviceToken(user_id=new_user.id, token=device_token)
            db.session.add(new_device_token)
        
        db.session.commit()

        # Return the new tokens and the user object, letting marshal_with handle formatting
        return {
            'access_token': access_token,
            'refresh_token': refresh_token_str,
            'user': new_user
        }, 201

@api.route('/logout')
class LogoutResource(Resource):
    @api.expect(api.model('LogoutRequest', {
        'refresh_token': fields.String(required=True),
        'device_token': fields.String(description='The device token to de-register')
    }))
    def post(self):
        """Logout the user by revoking their refresh token."""
        data = api.payload
        refresh_token_str = data.get('refresh_token')
        device_token_str = data.get('device_token')

        # Query the database for the refresh token
        refresh_token = RefreshToken.query.filter_by(token=refresh_token_str).first()

        if not refresh_token:
            return {'message': 'Invalid refresh token'}, 400

        # Revoke the token by deleting it
        db.session.delete(refresh_token)
        
        # If a device token was provided, delete it as well
        if device_token_str:
            device_token = DeviceToken.query.filter_by(token=device_token_str).first()
            if device_token:
                db.session.delete(device_token)

        db.session.commit()

        return {'message': 'Logged out successfully'}, 200

@api.route('/user/profile')
class UserProfileResource(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.marshal_with(user_model)
    def get(self):
        """Retrieve the profile of the authenticated user."""
        current_user = request.current_user
        return current_user, 200