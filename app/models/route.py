# app/models/route.py

from app.extensions import db

class Route(db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    train_number = db.Column(db.BigInteger, db.ForeignKey('trains.train_number'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    scheduled_arrival_time = db.Column(db.Time)
    scheduled_departure_time = db.Column(db.Time)

    station = db.relationship('Station', backref='routes')

    train = db.relationship('Train', back_populates='routes')

    def __repr__(self):
        return f"<Route {self.id} for Train {self.train_number}>"