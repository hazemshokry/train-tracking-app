# app/models/notification.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.mysql import CHAR


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(CHAR(36), db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.String(255), db.ForeignKey('trains.train_number'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='notifications')
    train = db.relationship('Train', backref='notifications')

    def __repr__(self):
        return f"<Notification {self.title} for User {self.user_id}>"