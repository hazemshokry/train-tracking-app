# app/models/station.py

from app.extensions import db

class Station(db.Model):
    __tablename__ = 'stations'

    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(50))
    location_lat = db.Column(db.Numeric(9, 6))
    location_long = db.Column(db.Numeric(9, 6))
    # 'arrival_time': fields.String,     # Add this line
    # 'departure_time': fields.String,   # Add this line if needed

    def __repr__(self):
        return f"<Station {self.name_en}>"