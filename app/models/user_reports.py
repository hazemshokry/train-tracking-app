# app/models/user_reports.py
# REPLACE your existing user_reports.py with this enhanced version

from app.extensions import db
from datetime import datetime, timedelta
from enum import Enum

class ReportType(Enum):
    ARRIVAL = 'arrival'
    DEPARTURE = 'departure'
    ONBOARD = 'onboard'
    OFFBOARD = 'offboard'
    PASSING = 'passing'
    DELAYED = 'delayed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    EARLY_ARRIVAL = 'early_arrival'
    BREAKDOWN = 'breakdown'

class ValidationStatus(Enum):
    PENDING = 'pending'
    VALIDATED = 'validated'
    REJECTED = 'rejected'
    FLAGGED = 'flagged'

class UserReport(db.Model):
    __tablename__ = 'user_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    train_number = db.Column(db.BigInteger, nullable=False)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    
    # Enhanced report types
    report_type = db.Column(db.Enum(
        'arrival', 'departure', 'onboard', 'offboard', 'passing', 
        'delayed', 'cancelled', 'no_show', 'early_arrival', 'breakdown'
    ), nullable=False)
    
    reported_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Enhanced validation and confidence fields
    is_valid = db.Column(db.Boolean, default=True)
    confidence_score = db.Column(db.Float, default=0.5)  # 0.0 to 1.0
    weight_factor = db.Column(db.Float, default=0.6)
    validation_status = db.Column(db.Enum('pending', 'validated', 'rejected', 'flagged'), default='pending')
    
    # Location validation
    reported_lat = db.Column(db.Numeric(9, 6))
    reported_long = db.Column(db.Numeric(9, 6))
    location_accuracy = db.Column(db.Float)  # GPS accuracy in meters
    
    # Additional context
    delay_minutes = db.Column(db.Integer)  # For delayed reports
    notes = db.Column(db.Text)  # Optional user notes
    is_intermediate_station = db.Column(db.Boolean, default=False)  # For non-route stations
    
    # Admin fields
    admin_verified = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='reports')
    operation = db.relationship('Operation', backref='reports')
    station = db.relationship('Station', backref='reports')
    verifier = db.relationship('User', foreign_keys=[verified_by])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set weight factor based on user reliability when creating new report
        if self.user_id and not self.weight_factor:
            from .user_reliability import UserReliability
            reliability = UserReliability.get_or_create(self.user_id)
            self.weight_factor = reliability.get_weight_factor()
    
    def is_negative_report(self):
        """Check if this is a negative report (train issues)"""
        negative_types = ['no_show', 'cancelled', 'breakdown', 'delayed']
        return self.report_type in negative_types
    
    def is_movement_report(self):
        """Check if this is a movement report (arrival/departure)"""
        movement_types = ['arrival', 'departure', 'passing', 'early_arrival']
        return self.report_type in movement_types
    
    def is_passenger_report(self):
        """Check if this is a passenger activity report"""
        passenger_types = ['onboard', 'offboard']
        return self.report_type in passenger_types
    
    def get_expected_time_window(self):
        """Get the expected time window for this report type"""
        windows = {
            'arrival': 30,      # 30 minutes
            'departure': 30,    # 30 minutes
            'onboard': 15,      # 15 minutes
            'offboard': 15,     # 15 minutes
            'passing': 10,      # 10 minutes
            'delayed': 60,      # 1 hour
            'no_show': 120,     # 2 hours
            'cancelled': 240,   # 4 hours
            'breakdown': 60,    # 1 hour
            'early_arrival': 30 # 30 minutes
        }
        return windows.get(self.report_type, 30)
    
    def calculate_time_score(self, scheduled_time):
        """Calculate time-based validation score"""
        if not scheduled_time:
            return 0.6  # Neutral score if no scheduled time
        
        time_diff = abs((self.reported_time - scheduled_time).total_seconds() / 60)
        expected_window = self.get_expected_time_window()
        
        if time_diff <= expected_window:
            return 1.0
        elif time_diff <= expected_window * 2:
            return 0.8
        elif time_diff <= expected_window * 4:
            return 0.6
        elif time_diff <= expected_window * 8:
            return 0.4
        else:
            return 0.2
    
    def update_confidence_score(self, validation_results):
        """Update confidence score based on validation results"""
        if not validation_results:
            return
        
        total_weight = 0
        weighted_score = 0
        
        for validation in validation_results:
            weight = validation.get_weight()
            total_weight += weight
            weighted_score += validation.score * weight
        
        if total_weight > 0:
            self.confidence_score = min(1.0, weighted_score / total_weight)
        
        # Update validation status based on confidence
        if self.confidence_score >= 0.8:
            self.validation_status = 'validated'
        elif self.confidence_score >= 0.5:
            self.validation_status = 'pending'
        elif self.confidence_score >= 0.3:
            self.validation_status = 'flagged'
        else:
            self.validation_status = 'rejected'
    
    def to_dict(self):
        """Convert report to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'train_number': self.train_number,
            'operation_id': self.operation_id,
            'station_id': self.station_id,
            'report_type': self.report_type,
            'reported_time': self.reported_time.isoformat(),
            'created_at': self.created_at.isoformat(),
            'confidence_score': self.confidence_score,
            'weight_factor': self.weight_factor,
            'validation_status': self.validation_status,
            'is_valid': self.is_valid,
            'delay_minutes': self.delay_minutes,
            'notes': self.notes,
            'is_intermediate_station': self.is_intermediate_station,
            'admin_verified': self.admin_verified,
            'location': {
                'lat': float(self.reported_lat) if self.reported_lat else None,
                'long': float(self.reported_long) if self.reported_long else None,
                'accuracy': self.location_accuracy
            } if self.reported_lat and self.reported_long else None
        }
    
    @staticmethod
    def get_recent_reports_for_validation(train_number, station_id, hours=2):
        """Get recent reports for validation purposes"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return UserReport.query.filter(
            UserReport.train_number == train_number,
            UserReport.station_id == station_id,
            UserReport.created_at >= cutoff_time,
            UserReport.validation_status.in_(['validated', 'pending'])
        ).order_by(UserReport.created_at.desc()).all()
    
    @staticmethod
    def check_duplicate(user_id, train_number, station_id, report_type, minutes=5):
        """Check for duplicate reports within time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        return UserReport.query.filter(
            UserReport.user_id == user_id,
            UserReport.train_number == train_number,
            UserReport.station_id == station_id,
            UserReport.report_type == report_type,
            UserReport.created_at >= cutoff_time
        ).first()
    
    def __repr__(self):
        return f"<UserReport {self.id} User {self.user_id} Train {self.train_number} {self.report_type}>"

