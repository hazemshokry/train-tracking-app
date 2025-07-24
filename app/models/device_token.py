# app/models/device_token.py
from app.extensions import db
from sqlalchemy.dialects.mysql import CHAR

class DeviceToken(db.Model):
    __tablename__ = 'device_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(CHAR(36), db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref='device_tokens')

    def __repr__(self):
        return f"<DeviceToken for User {self.user_id}>"