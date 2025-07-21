# app/models/user_reports.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.dialects.mysql import CHAR


class UserReport(db.Model):
    __tablename__ = 'user_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(CHAR(36), db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.String(255), nullable=False)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    
    # --- Updated Enum ---
    report_type = db.Column(db.Enum('arrival', 'departure', 'onboard', 'offboard', 'delay', 'cancelled', 'passed_station'), nullable=False)
    
    reported_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # --- New Fields ---
    report_location_lat = db.Column(db.Numeric(9, 6), nullable=True)
    report_location_long = db.Column(db.Numeric(9, 6), nullable=True)
    confidence_score = db.Column(db.Float, default=0.0)
    is_valid = db.Column(db.Boolean, default=False) # Default to False until validated

    user = db.relationship('User', backref='reports')
    operation = db.relationship('Operation', backref='reports')
    station = db.relationship('Station', backref='reports')

    def __repr__(self):
        return f"<UserReport User {self.user_id} Train {self.train_number} Station {self.station_id}>"