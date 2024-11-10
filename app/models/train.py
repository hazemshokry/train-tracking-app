# app/models/train.py

from app.extensions import db

class Train(db.Model):
    __tablename__ = 'trains'

    train_number = db.Column(db.BigInteger, primary_key=True)
    train_type = db.Column(db.String(50))

    departure_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    arrival_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)

    scheduled_departure_time = db.Column(db.Time, nullable=False)
    scheduled_arrival_time = db.Column(db.Time, nullable=False)

    departure_station = db.relationship('Station', foreign_keys=[departure_station_id], backref='departing_trains')
    arrival_station = db.relationship('Station', foreign_keys=[arrival_station_id], backref='arriving_trains')

    routes = db.relationship('Route', back_populates='train')

    def __repr__(self):
        return f"<Train {self.train_number}>"