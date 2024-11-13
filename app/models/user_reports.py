# app/models/user_reports.py

from app.extensions import db
from datetime import datetime

class UserReport(db.Model):
    __tablename__ = 'userreports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.BigInteger, nullable=False)  # Keep train_number in UserReport
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)  # Reference to Operations
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    report_type = db.Column(db.Enum('arrival', 'departure', 'onboard', 'offboard'), nullable=False)
    reported_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_valid = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='reports')
    operation = db.relationship('Operation', backref='reports')  # New relationship to Operations
    station = db.relationship('Station', backref='reports')

    def __repr__(self):
        return f"<UserReport User {self.user_id} Train {self.train_number} Operation {self.operation_id} Station {self.station_id}>"