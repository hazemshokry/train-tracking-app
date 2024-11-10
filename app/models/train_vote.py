# app/models/train_vote.py

from app.extensions import db

class TrainVote(db.Model):
    __tablename__ = 'train_votes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # Assuming user ID is required
    train_id = db.Column(db.Integer, db.ForeignKey('trains.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    is_almost_correct = db.Column(db.Boolean, nullable=False)
    user_status = db.Column(db.String(20), nullable=False)

    def __init__(self, user_id, train_id, station_id, is_correct, is_almost_correct, user_status):
        self.user_id = user_id
        self.train_id = train_id
        self.station_id = station_id
        self.is_correct = is_correct
        self.is_almost_correct = is_almost_correct
        self.user_status = user_status