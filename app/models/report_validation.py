# app/models/report_validation.py
# Add this new model to your existing models directory

from app.extensions import db
from datetime import datetime
from enum import Enum

class ValidationType(Enum):
    TIME_CHECK = 'time_check'
    LOCATION_CHECK = 'location_check'
    CONSISTENCY_CHECK = 'consistency_check'
    PATTERN_CHECK = 'pattern_check'
    ROUTE_CHECK = 'route_check'
    ADMIN_REVIEW = 'admin_review'
    RATE_LIMIT_CHECK = 'rate_limit_check'
    DUPLICATE_CHECK = 'duplicate_check'

class ValidationResult(Enum):
    PASSED = 'passed'
    FAILED = 'failed'
    WARNING = 'warning'

class ReportValidation(db.Model):
    __tablename__ = 'report_validations'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('user_reports.id'), nullable=False)
    validation_type = db.Column(db.Enum(
        'time_check', 'location_check', 'consistency_check', 
        'pattern_check', 'route_check', 'admin_review',
        'rate_limit_check', 'duplicate_check'
    ), nullable=False)
    
    status = db.Column(db.Enum('passed', 'failed', 'warning'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Validation score 0.0 to 1.0
    weight = db.Column(db.Float, default=1.0)    # Weight of this validation
    
    details = db.Column(db.Text)  # JSON stored as text for SQLite compatibility
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    processed_by = db.Column(db.String(100))  # Which validator processed this
    
    # Validation weights for different types
    VALIDATION_WEIGHTS = {
        'time_check': 0.25,
        'location_check': 0.20,
        'consistency_check': 0.20,
        'pattern_check': 0.15,
        'route_check': 0.15,
        'admin_review': 0.30,
        'rate_limit_check': 0.10,
        'duplicate_check': 0.10
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default weight based on validation type
        if not self.weight and self.validation_type:
            self.weight = self.VALIDATION_WEIGHTS.get(self.validation_type, 1.0)
    
    def get_weight(self):
        """Get the weight for this validation"""
        return self.weight or self.VALIDATION_WEIGHTS.get(self.validation_type, 1.0)
    
    def is_critical_failure(self):
        """Check if this is a critical validation failure"""
        critical_types = ['rate_limit_check', 'duplicate_check', 'admin_review']
        return (self.validation_type in critical_types and 
                self.status == 'failed')
    
    def to_dict(self):
        """Convert validation to dictionary"""
        return {
            'id': self.id,
            'validation_type': self.validation_type,
            'status': self.status,
            'score': self.score,
            'weight': self.get_weight(),
            'details': self.details,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'processed_by': self.processed_by
        }
    
    @staticmethod
    def create_validation_result(report_id, validation_type, status, score, 
                               details=None, error_message=None, processed_by=None):
        """Create a new validation result"""
        validation = ReportValidation(
            report_id=report_id,
            validation_type=validation_type,
            status=status,
            score=score,
            details=details,
            error_message=error_message,
            processed_by=processed_by
        )
        return validation
    
    def __repr__(self):
        return f"<ReportValidation {self.id} {self.validation_type} {self.status} {self.score}>"

