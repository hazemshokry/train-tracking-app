# app/routes/user_routes.py

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from app.models.user import User
from app.extensions import db
from datetime import datetime
import jwt  # For token generation
import os

api = Namespace('users', description='User related operations')

# Environment variable for secret key (ensure this is set in your config)
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

# Serializer models
user_model = api.model('User', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the user'),
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'phone_number': fields.String(required=True, description='Phone number'),
    'is_active': fields.Boolean(description='Active status'),
    'date_joined': fields.DateTime(description='Date joined'),
    'last_login': fields.DateTime(description='Last login time'),
})

user_create_model = api.model('UserCreate', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'phone_number': fields.String(required=True, description='Phone number'),
    'password': fields.String(required=True, description='Password', min_length=6),
})

user_login_model = api.model('UserLogin', {
    'username': fields.String(required=True, description='Username or email'),
    'password': fields.String(required=True, description='Password'),
})

token_model = api.model('Token', {
    'token': fields.String(description='Authentication token'),
})

@api.route('/register')
class UserRegister(Resource):
    @api.expect(user_create_model)
    @api.marshal_with(user_model, code=201)
    def post(self):
        """Register a new user"""
        data = api.payload
        username = data['username']
        email = data['email']
        phone_number = data['phone_number']
        password = data['password']

        if User.query.filter((User.username == username) | (User.email == email)).first():
            api.abort(400, 'Username or email already exists')

        new_user = User(
            username=username,
            email=email,
            phone_number=phone_number,
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return new_user, 201

@api.route('/login')
class UserLogin(Resource):
    @api.expect(user_login_model)
    @api.marshal_with(token_model)
    def post(self):
        """Authenticate a user and return a token"""
        data = api.payload
        username_or_email = data['username']
        password = data['password']

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            token = jwt.encode(
                {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(hours=24)},
                SECRET_KEY,
                algorithm='HS256'
            )
            user.last_login = datetime.utcnow()
            db.session.commit()
            return {'token': token}
        else:
            api.abort(401, 'Invalid credentials')

def token_required(f):
    """Decorator to check for a valid token"""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check for token in header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']

        if not token:
            api.abort(401, 'Token is missing')

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                api.abort(401, 'User not found')
        except jwt.ExpiredSignatureError:
            api.abort(401, 'Token has expired')
        except jwt.InvalidTokenError:
            api.abort(401, 'Invalid token')

        # Attach current_user to the request context
        request.current_user = current_user

        return f(*args, **kwargs)

    return decorated

@api.route('/<int:id>')
@api.param('id', 'The user identifier')
class UserResource(Resource):
    @api.marshal_with(user_model)
    def get(self, id):
        """Get a user by ID"""
        user = User.query.get_or_404(id)
        # Ensure the user is accessing their own data
        if request.current_user.id != user.id:
            api.abort(403, 'Access forbidden')
        return user

    @api.expect(user_create_model)
    @api.marshal_with(user_model)
    def put(self, id):
        """Update a user by ID"""
        user = User.query.get_or_404(id)
        # Ensure the user is updating their own data
        if request.current_user.id != user.id:
            api.abort(403, 'Access forbidden')

        data = api.payload
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.phone_number = data.get('phone_number', user.phone_number)
        if 'password' in data:
            user.set_password(data['password'])
        db.session.commit()
        return user

    @api.response(204, 'User deleted')
    def delete(self, id):
        """Delete a user by ID"""
        user = User.query.get_or_404(id)
        # Ensure the user is deleting their own account
        if request.current_user.id != user.id:
            api.abort(403, 'Access forbidden')

        db.session.delete(user)
        db.session.commit()
        return '', 204

@api.route('/list')
class UserList(Resource):
    # @api.doc(security='apikey')  # Requires authentication
    # @token_required  # Apply the token_required decorator
    @api.marshal_list_with(user_model)
    def get(self):
        """List all users"""
        users = User.query.all()
        return users