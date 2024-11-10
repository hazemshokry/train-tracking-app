# app/models/reward.py

from app.extensions import db
from datetime import datetime

class Reward(db.Model):
    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    date_awarded = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(255))

    user = db.relationship('User', backref='rewards')

    def __repr__(self):
        return f"<Reward {self.points} points to User {self.user_id}>"