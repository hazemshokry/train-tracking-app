# app/models/calculated_times.py

from app.extensions import db

class CalculatedTime(db.Model):
    __tablename__ = 'calculatedtimes'

    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.BigInteger, db.ForeignKey('trains.train_number'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    calculated_arrival_time = db.Column(db.DateTime)
    calculated_departure_time = db.Column(db.DateTime)
    number_of_reports = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    train = db.relationship('Train', backref='calculated_times')
    station = db.relationship('Station', backref='calculated_times')

    def __repr__(self):
        return f"<CalculatedTime Train {self.train_number} Station {self.station_id}>"