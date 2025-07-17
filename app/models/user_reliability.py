# app/models/user_reliability.py
# Add this new model to your existing models directory

from app.extensions import db
from datetime import datetime

class UserReliability(db.Model):
    __tablename__ = 'user_reliability'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    reliability_score = db.Column(db.Float, default=0.6)  # 0.0 to 1.0
    total_reports = db.Column(db.Integer, default=0)
    accurate_reports = db.Column(db.Integer, default=0)
    flagged_reports = db.Column(db.Integer, default=0)
    spam_reports = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_type = db.Column(db.Enum('admin', 'verified', 'regular', 'new', 'flagged'), default='new')
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reliability', uselist=False))
    
    # Weight factors based on user type
    WEIGHT_FACTORS = {
        'admin': 1.0,
        'verified': 0.8,
        'regular': 0.6,
        'new': 0.4,
        'flagged': 0.2
    }
    
    def get_weight_factor(self):
        """Get the weight factor for this user's reports"""
        return self.WEIGHT_FACTORS.get(self.user_type, 0.4)
    
    def update_reliability(self, report_outcome):
        """Update reliability score based on report outcome"""
        self.total_reports += 1
        
        if report_outcome == 'accurate':
            self.accurate_reports += 1
        elif report_outcome == 'flagged':
            self.flagged_reports += 1
        elif report_outcome == 'spam':
            self.spam_reports += 1
        
        # Calculate new reliability score
        if self.total_reports > 0:
            accuracy_rate = self.accurate_reports / self.total_reports
            flag_rate = self.flagged_reports / self.total_reports
            spam_rate = self.spam_reports / self.total_reports
            
            # Base score on accuracy, penalize for flags and spam
            self.reliability_score = max(0.1, min(1.0, 
                accuracy_rate - (flag_rate * 0.3) - (spam_rate * 0.5)
            ))
        
        # Update user type based on reliability and report count
        self._update_user_type()
        self.last_updated = datetime.utcnow()
    
    def _update_user_type(self):
        """Update user type based on reliability metrics"""
        if self.user_type == 'admin':
            return  # Admin type is manually set
        
        if self.spam_reports > 5 or self.reliability_score < 0.3:
            self.user_type = 'flagged'
        elif self.total_reports >= 50 and self.reliability_score >= 0.8:
            self.user_type = 'verified'
        elif self.total_reports >= 10 and self.reliability_score >= 0.6:
            self.user_type = 'regular'
        else:
            self.user_type = 'new'
    
    def can_report(self):
        """Check if user can submit reports based on their status"""
        if self.user_type == 'flagged' and self.spam_reports > 10:
            return False, "Account flagged for excessive spam reports"
        return True, "OK"
    
    def get_rate_limits(self):
        """Get rate limits for this user type"""
        limits = {
            'admin': {'per_minute': 100, 'per_hour': 1000, 'per_day': 10000},
            'verified': {'per_minute': 10, 'per_hour': 100, 'per_day': 1000},
            'regular': {'per_minute': 5, 'per_hour': 50, 'per_day': 500},
            'new': {'per_minute': 2, 'per_hour': 20, 'per_day': 100},
            'flagged': {'per_minute': 1, 'per_hour': 5, 'per_day': 20}
        }
        return limits.get(self.user_type, limits['new'])
    
    def __repr__(self):
        return f"<UserReliability User {self.user_id} Type {self.user_type} Score {self.reliability_score:.2f}>"

    @staticmethod
    def get_or_create(user_id):
        """Get existing reliability record or create new one"""
        reliability = UserReliability.query.filter_by(user_id=user_id).first()
        if not reliability:
            reliability = UserReliability(user_id=user_id)
            db.session.add(reliability)
            db.session.flush()
        return reliability

