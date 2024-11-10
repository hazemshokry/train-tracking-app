# app/models/user_favourite_trains.py

from app.extensions import db
from datetime import datetime

class UserFavouriteTrain(db.Model):
    __tablename__ = 'userfavouritetrains'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.BigInteger, db.ForeignKey('trains.train_number'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='favourite_trains')
    train = db.relationship('Train', backref='favourited_by')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'train_number', name='unique_user_train'),
    )

    def __repr__(self):
        return f"<UserFavouriteTrain User {self.user_id} Train {self.train_number}>"