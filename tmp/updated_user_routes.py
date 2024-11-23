import random
import time
from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from app.models.user import User
from app.extensions import db
import jwt
from datetime import datetime, timedelta
import os
from functools import wraps

api = Namespace('users', description='User related operations')

# Environment variable for secret key
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# In-memory storage for OTPs
otp_storage = {}

# Add a model for phone number input
phone_number_model = api.model('PhoneNumberInput', {
    'phone_number': fields.String(required=True, description='The phone number to receive the OTP')
})

# Add a model for OTP verification input
otp_verification_model = api.model('OTPVerificationInput', {
    'phone_number': fields.String(required=True, description='The phone number used to send the OTP'),
    'otp': fields.Integer(required=True, description='The OTP received by the user')
})

# Helper function to generate OTP
def generate_otp():
    return random.randint(100000, 999999)

    

# Helper function to generate JWT token
def generate_jwt(user_id):
    expiration = datetime.utcnow() + timedelta(days=1)  # Token valid for 1 day
    token = jwt.encode({'id': user_id, 'exp': expiration}, SECRET_KEY, algorithm='HS256')
    return token

# Secret key for JWT
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')  # Expecting "Bearer <token>"

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            # Remove "Bearer " from the token if present
            token = token.replace("Bearer ", "")
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = decoded['id']
            current_user = User.query.get(user_id)
            if not current_user:
                return jsonify({"error": "Invalid token"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# 1. Phone Number Submission
@api.route('/submit-phone')
class SubmitPhone(Resource):
    @api.expect(phone_number_model)  # Attach the model for input validation and documentation
    def post(self):
        """
        Submit a phone number to receive an OTP.
        """
        data = request.json
        phone_number = data.get('phone_number')

        if not phone_number:
            return {"error": "Phone number is required"}, 400

        otp = generate_otp()
        otp_storage[phone_number] = {"otp": otp, "expiry": time.time() + 300}  # OTP valid for 5 minutes

        # Simulate sending OTP
        print(f"Sending OTP {otp} to phone number {phone_number}")

        return {"message": "OTP sent successfully"}, 200

# 2. OTP Verification
@api.route('/verify-otp')
class VerifyOtp(Resource):
    @api.expect(otp_verification_model)  # Attach the model for input validation and documentation
    def post(self):
        """
        Verify the OTP submitted by the user.
        """
        data = request.json
        phone_number = data.get('phone_number')
        otp = data.get('otp')

        # Validate input
        if not phone_number or not otp:
            return {"error": "Phone number and OTP are required"}, 400

        # Check if OTP is valid
        stored_otp = otp_storage.get(phone_number)
        if stored_otp and time.time() < stored_otp["expiry"] and stored_otp["otp"] == int(otp):
            otp_storage.pop(phone_number, None)  # Clear OTP after successful verification

            # Check if the user exists
            user = User.query.filter_by(phone_number=phone_number).first()
            if user:
                # Generate JWT for existing user
                token = generate_jwt(user.id)
                return {"message": "Login successful", "token": token}, 200
            else:
                # New user, proceed to registration
                return {"message": "New user, proceed to registration"}, 200
        else:
            return {"error": "Invalid or expired OTP"}, 400

# 3. User Registration
@api.route('/register-user')
class RegisterUser(Resource):
    @api.expect(user_registration_model)  # Attach the model for input validation and documentation
    def post(self):
        """
        Register a new user with the provided details.
        """
        data = request.json

        # Extract required fields
        phone_number = data.get('phone_number')
        username = data.get('username')
        email = data.get('email')

        # Extract optional fields
        date_of_birth = data.get('date_of_birth')
        address = data.get('address')

        # Validate required fields
        if not phone_number or not username or not email:
            return {"error": "Phone number, username, and email are required"}, 400

        # Check if the user already exists
        user_exists = User.query.filter_by(phone_number=phone_number).first()
        if user_exists:
            return {"error": "User already exists"}, 400

        # Register the new user
        new_user = User(
            phone_number=phone_number,
            username=username,
            email=email,
            date_of_birth=date_of_birth,
            address=address,
            date_joined=datetime.utcnow(),
            is_active=True
        )
        db.session.add(new_user)
        db.session.commit()

        # Return success response
        return {"message": "User registered successfully", "user_id": new_user.id}, 200