# app/models/train_subscription.py

from app.extensions import db
from datetime import datetime

class TrainSubscription(db.Model):
    __tablename__ = 'train_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.CHAR(36), db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.String(255), db.ForeignKey('trains.train_number'), nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='subscriptions')
    train = db.relationship('Train', backref='subscribers')

    def __repr__(self):
        return f"<TrainSubscription User {self.user_id} Train {self.train_number}>"