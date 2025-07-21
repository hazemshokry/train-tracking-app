# app/models/refresh_token.py
from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.mysql import CHAR

class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False, unique=True)
    user_id = db.Column(CHAR(36), db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy='dynamic'))

    def __repr__(self):
        return f"<RefreshToken {self.token} for User {self.user_id}>"