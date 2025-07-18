# app/models/user.py

from app.extensions import db
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

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone_number = db.Column(db.String(255), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    date_joined = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_login = db.Column(db.DateTime)
    
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