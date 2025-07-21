# app/models/user.py
import uuid
from app.extensions import db
from sqlalchemy.dialects.mysql import CHAR
from enum import Enum

# Inherit from str to ensure values are treated as strings
class UserType(str, Enum):
    ADMIN = 'admin'
    VERIFIED = 'verified'
    REGULAR = 'regular'
    NEW = 'new'
    FLAGGED = 'flagged'

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone_number = db.Column(db.String(255), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime)
    
    # --- ADDED FOR FIREBASE ---
    device_token = db.Column(db.String(255), nullable=True) # To store Firebase device token
    
    # --- THE FINAL FIX IS HERE ---
    # This tells SQLAlchemy to use VARCHAR instead of a native ENUM,
    # which resolves the case-sensitivity and mapping issue.
    user_type = db.Column(
        db.Enum(
            UserType,
            name="usertype",              # same as enum name in DB
            native_enum=False,           # store as VARCHAR
            values_callable=lambda obj: [e.value for e in obj]  # important!
        ),
        default=UserType.NEW,
        nullable=False
    )
    
    reliability_score = db.Column(db.Float, default=0.5, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"