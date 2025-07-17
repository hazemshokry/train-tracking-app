# app/models/calculated_times.py
# REPLACE your existing calculated_times.py with this enhanced version

from app.extensions import db
from datetime import datetime, timedelta

class CalculatedTime(db.Model):
    __tablename__ = 'calculated_times'

    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.BigInteger, db.ForeignKey('trains.train_number'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    
    # Enhanced time calculations
    calculated_arrival_time = db.Column(db.DateTime)
    calculated_departure_time = db.Column(db.DateTime)
    scheduled_arrival_time = db.Column(db.DateTime)
    scheduled_departure_time = db.Column(db.DateTime)
    
    # Previous calculations for comparison
    previous_arrival_time = db.Column(db.DateTime)
    previous_departure_time = db.Column(db.DateTime)
    
    # Enhanced metrics
    number_of_reports = db.Column(db.Integer, default=0)
    confidence_level = db.Column(db.Float, default=0.5)  # 0.0 to 1.0
    weighted_reports = db.Column(db.Float, default=0.0)  # Sum of weight factors
    
    # Status tracking
    status = db.Column(db.Enum('scheduled', 'estimated', 'confirmed', 'passed', 'cancelled', 'delayed'), default='scheduled')
    delay_minutes = db.Column(db.Integer, default=0)
    
    # Update tracking
    last_updated = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_report_time = db.Column(db.DateTime)
    update_count = db.Column(db.Integer, default=0)
    
    # Admin override capabilities
    admin_override = db.Column(db.Boolean, default=False)
    admin_time = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    overridden_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    overridden_at = db.Column(db.DateTime)

    # Relationships
    train = db.relationship('Train', backref='calculated_times')
    station = db.relationship('Station', backref='calculated_times')
    admin_user = db.relationship('User', foreign_keys=[overridden_by])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.scheduled_arrival_time and not self.scheduled_departure_time:
            self._set_scheduled_times()
    
    def _set_scheduled_times(self):
        """Set scheduled times from route information"""
        from app.models.route import Route
        from app.models.operations import Operation
        
        # Get operation for this train to get the operational date
        operation = Operation.query.filter_by(train_number=self.train_number).first()
        if not operation:
            return
            
        route = Route.query.filter_by(
            train_number=self.train_number,
            station_id=self.station_id
        ).first()
        
        if route:
            # Convert time to datetime using operation date
            operation_date = operation.operational_date
            
            if route.scheduled_arrival_time:
                self.scheduled_arrival_time = datetime.combine(
                    operation_date, route.scheduled_arrival_time
                )
            
            if route.scheduled_departure_time:
                self.scheduled_departure_time = datetime.combine(
                    operation_date, route.scheduled_departure_time
                )
    
    def update_from_reports(self, reports):
        """Update calculated times based on new reports"""
        if not reports:
            return
        
        # Store previous times for comparison
        self.previous_arrival_time = self.calculated_arrival_time
        self.previous_departure_time = self.calculated_departure_time
        
        # Calculate weighted average times
        arrival_reports = [r for r in reports if r.is_movement_report() and 
                          r.report_type in ['arrival', 'early_arrival']]
        departure_reports = [r for r in reports if r.is_movement_report() and 
                           r.report_type == 'departure']
        
        if arrival_reports:
            self.calculated_arrival_time = self._calculate_weighted_time(arrival_reports)
        
        if departure_reports:
            self.calculated_departure_time = self._calculate_weighted_time(departure_reports)
        
        # Update metrics
        self.number_of_reports = len(reports)
        self.weighted_reports = sum(r.weight_factor * r.confidence_score for r in reports)
        self.confidence_level = self._calculate_confidence_level(reports)
        
        # Update delay calculation
        self._update_delay()
        
        # Update status
        self._update_status(reports)
        
        # Track update
        self.last_updated = datetime.utcnow()
        self.last_report_time = max(r.created_at for r in reports)
        self.update_count += 1
    
    def _calculate_weighted_time(self, reports):
        """Calculate weighted average time from reports"""
        if not reports:
            return None
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for report in reports:
            weight = report.weight_factor * report.confidence_score
            total_weight += weight
            weighted_sum += report.reported_time.timestamp() * weight
        
        if total_weight > 0:
            return datetime.fromtimestamp(weighted_sum / total_weight)
        
        return None
    
    def _calculate_confidence_level(self, reports):
        """Calculate confidence level based on reports"""
        if not reports:
            return 0.5
        
        # Base confidence on number of reports and their quality
        report_count_factor = min(1.0, len(reports) / 5.0)  # Max at 5 reports
        
        # Average confidence of reports
        avg_confidence = sum(r.confidence_score for r in reports) / len(reports)
        
        # Weight factor consideration
        avg_weight = sum(r.weight_factor for r in reports) / len(reports)
        
        # Combine factors
        confidence = (report_count_factor * 0.3 + avg_confidence * 0.4 + avg_weight * 0.3)
        
        return min(1.0, confidence)
    
    def _update_delay(self):
        """Update delay calculation"""
        if self.calculated_arrival_time and self.scheduled_arrival_time:
            delay = (self.calculated_arrival_time - self.scheduled_arrival_time).total_seconds() / 60
            self.delay_minutes = int(delay)
        elif self.calculated_departure_time and self.scheduled_departure_time:
            delay = (self.calculated_departure_time - self.scheduled_departure_time).total_seconds() / 60
            self.delay_minutes = int(delay)
        else:
            self.delay_minutes = 0
    
    def _update_status(self, reports):
        """Update status based on reports"""
        if self.admin_override:
            return  # Don't change admin-set status
        
        # Check for negative reports
        negative_reports = [r for r in reports if r.is_negative_report()]
        
        if any(r.report_type == 'cancelled' for r in negative_reports):
            self.status = 'cancelled'
        elif any(r.report_type == 'no_show' for r in negative_reports):
            self.status = 'cancelled'
        elif any(r.report_type == 'breakdown' for r in negative_reports):
            self.status = 'delayed'
        elif self.delay_minutes > 15:
            self.status = 'delayed'
        elif self.confidence_level >= 0.8:
            self.status = 'confirmed'
        elif self.number_of_reports > 0:
            self.status = 'estimated'
        else:
            self.status = 'scheduled'
    
    def get_best_time_estimate(self, time_type='arrival'):
        """Get the best available time estimate"""
        if self.admin_override and self.admin_time:
            return self.admin_time
        
        if time_type == 'arrival':
            return (self.calculated_arrival_time or 
                   self.scheduled_arrival_time)
        else:
            return (self.calculated_departure_time or 
                   self.scheduled_departure_time)
    
    def is_time_passed(self):
        """Check if the estimated time has passed"""
        now = datetime.utcnow()
        best_time = self.get_best_time_estimate()
        return best_time and now > best_time + timedelta(minutes=30)
    
    def get_time_until_arrival(self):
        """Get minutes until estimated arrival"""
        arrival_time = self.get_best_time_estimate('arrival')
        if not arrival_time:
            return None
        
        now = datetime.utcnow()
        diff = (arrival_time - now).total_seconds() / 60
        return int(diff)
    
    def admin_override_time(self, admin_user_id, override_time, notes=None):
        """Allow admin to override calculated time"""
        self.admin_override = True
        self.admin_time = override_time
        self.admin_notes = notes
        self.overridden_by = admin_user_id
        self.overridden_at = datetime.utcnow()
        self.confidence_level = 1.0  # Admin override has highest confidence
    
    def clear_admin_override(self):
        """Clear admin override and return to calculated times"""
        self.admin_override = False
        self.admin_time = None
        self.admin_notes = None
        self.overridden_by = None
        self.overridden_at = None
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'train_number': self.train_number,
            'station_id': self.station_id,
            'calculated_arrival_time': self.calculated_arrival_time.isoformat() if self.calculated_arrival_time else None,
            'calculated_departure_time': self.calculated_departure_time.isoformat() if self.calculated_departure_time else None,
            'scheduled_arrival_time': self.scheduled_arrival_time.isoformat() if self.scheduled_arrival_time else None,
            'scheduled_departure_time': self.scheduled_departure_time.isoformat() if self.scheduled_departure_time else None,
            'confidence_level': self.confidence_level,
            'number_of_reports': self.number_of_reports,
            'weighted_reports': self.weighted_reports,
            'status': self.status,
            'delay_minutes': self.delay_minutes,
            'last_updated': self.last_updated.isoformat(),
            'admin_override': self.admin_override,
            'admin_time': self.admin_time.isoformat() if self.admin_time else None,
            'time_until_arrival': self.get_time_until_arrival()
        }
    
    @staticmethod
    def get_or_create_by_operation(operation_id, station_id):
        """Get existing calculated time or create new one using operation_id"""
        from app.models.operations import Operation
        
        operation = Operation.query.get(operation_id)
        if not operation:
            return None
            
        calc_time = CalculatedTime.query.filter_by(
            train_number=operation.train_number,
            station_id=station_id
        ).first()
        
        if not calc_time:
            calc_time = CalculatedTime(
                train_number=operation.train_number,
                station_id=station_id
            )
            db.session.add(calc_time)
            db.session.flush()
        
        return calc_time

    def __repr__(self):
        return f"<CalculatedTime Train {self.train_number} Station {self.station_id} {self.status}>"

