# app/utils/validation_engine.py
# Add this new utility file to handle report validation

import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from app.extensions import db
from app.models.user_reports import UserReport
from app.models.user_reliability import UserReliability
from app.models.report_validation import ReportValidation
from app.models.route import Route

class ValidationEngine:
    """Main validation engine for train reports"""
    
    def __init__(self):
        self.validators = [
            TimeValidator(),
            LocationValidator(),
            ConsistencyValidator(),
            PatternValidator(),
            RouteValidator(),
            RateLimitValidator(),
            DuplicateValidator()
        ]
    
    def validate_report(self, report: UserReport) -> List[ReportValidation]:
        """Run all validations on a report and return results"""
        validations = []
        
        for validator in self.validators:
            try:
                validation = validator.validate(report)
                if validation:
                    validations.append(validation)
            except Exception as e:
                # Log error and create failed validation
                error_validation = ReportValidation.create_validation_result(
                    report_id=report.id,
                    validation_type=validator.get_validation_type(),
                    status='failed',
                    score=0.0,
                    error_message=f"Validation error: {str(e)}",
                    processed_by=validator.__class__.__name__
                )
                validations.append(error_validation)
        
        # Update report with validation results
        report.update_confidence_score(validations)
        
        return validations


class BaseValidator:
    """Base class for all validators"""
    
    def get_validation_type(self) -> str:
        """Return the validation type this validator handles"""
        raise NotImplementedError
    
    def validate(self, report: UserReport) -> ReportValidation:
        """Validate a report and return validation result"""
        raise NotImplementedError
    
    def _create_validation(self, report_id: int, status: str, 
                          score: float, details: str = None, 
                          error_message: str = None) -> ReportValidation:
        """Helper to create validation result"""
        return ReportValidation.create_validation_result(
            report_id=report_id,
            validation_type=self.get_validation_type(),
            status=status,
            score=score,
            details=details,
            error_message=error_message,
            processed_by=self.__class__.__name__
        )


class TimeValidator(BaseValidator):
    """Validates report timing against schedules and reasonable bounds"""
    
    def get_validation_type(self) -> str:
        return 'time_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        now = datetime.utcnow()
        report_time = report.reported_time
        
        # Check if report time is reasonable
        if report_time > now + timedelta(hours=2):
            return self._create_validation(
                report.id, 'failed', 0.0,
                f'Report time {(report_time - now).total_seconds() / 3600:.1f} hours in future',
                'Report time is too far in the future'
            )
        
        if report_time < now - timedelta(days=2):
            return self._create_validation(
                report.id, 'failed', 0.1,
                f'Report time {(now - report_time).days} days old',
                'Report time is too old'
            )
        
        # Get scheduled time for comparison
        scheduled_time = self._get_scheduled_time(report)
        if scheduled_time:
            score = report.calculate_time_score(scheduled_time)
            time_diff_minutes = abs((report_time - scheduled_time).total_seconds() / 60)
            
            if score >= 0.8:
                status = 'passed'
            elif score >= 0.5:
                status = 'warning'
            else:
                status = 'failed'
            
            return self._create_validation(
                report.id, status, score,
                f'Time difference: {time_diff_minutes:.1f} minutes from schedule'
            )
        
        # No scheduled time available - neutral score
        return self._create_validation(
            report.id, 'warning', 0.6,
            'No scheduled time available for comparison'
        )
    
    def _get_scheduled_time(self, report: UserReport) -> datetime:
        """Get scheduled time for the report's station and train"""
        route = Route.query.filter_by(
            train_number=report.train_number,
            station_id=report.station_id
        ).first()
        
        if not route:
            return None
        
        operation_date = report.operation.operational_date
        
        if report.report_type in ['arrival', 'early_arrival'] and route.scheduled_arrival_time:
            return datetime.combine(operation_date, route.scheduled_arrival_time)
        elif report.report_type == 'departure' and route.scheduled_departure_time:
            return datetime.combine(operation_date, route.scheduled_departure_time)
        
        return None


class LocationValidator(BaseValidator):
    """Validates report location against station coordinates"""
    
    def get_validation_type(self) -> str:
        return 'location_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        if not report.reported_lat or not report.reported_long:
            return self._create_validation(
                report.id, 'warning', 0.5,
                'No GPS coordinates provided'
            )
        
        station = report.station
        if not station.location_lat or not station.location_long:
            return self._create_validation(
                report.id, 'warning', 0.6,
                'Station coordinates not available'
            )
        
        # Calculate distance
        distance_km = self._calculate_distance(
            float(report.reported_lat), float(report.reported_long),
            float(station.location_lat), float(station.location_long)
        )
        
        # Score based on distance and report type
        score = self._calculate_location_score(distance_km, report.report_type)
        
        if score >= 0.8:
            status = 'passed'
        elif score >= 0.5:
            status = 'warning'
        else:
            status = 'failed'
        
        return self._create_validation(
            report.id, status, score,
            f'Distance from station: {distance_km:.2f}km'
        )
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _calculate_location_score(self, distance_km: float, report_type: str) -> float:
        """Calculate score based on distance and report type"""
        if report_type in ['arrival', 'departure', 'offboard']:
            # Station-based reports should be close to station
            if distance_km <= 1.0:
                return 1.0
            elif distance_km <= 3.0:
                return 0.8
            elif distance_km <= 10.0:
                return 0.5
            else:
                return 0.2
        elif report_type in ['onboard', 'passing']:
            # Train-based reports can be further from station
            if distance_km <= 5.0:
                return 1.0
            elif distance_km <= 20.0:
                return 0.8
            elif distance_km <= 50.0:
                return 0.6
            else:
                return 0.3
        else:
            # Other report types - moderate distance tolerance
            if distance_km <= 2.0:
                return 1.0
            elif distance_km <= 10.0:
                return 0.7
            else:
                return 0.4


class ConsistencyValidator(BaseValidator):
    """Validates report consistency with other recent reports"""
    
    def get_validation_type(self) -> str:
        return 'consistency_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        # Get recent reports for the same train and station
        recent_reports = UserReport.get_recent_reports_for_validation(
            report.train_number, report.station_id, hours=2
        )
        
        # Exclude the current report
        recent_reports = [r for r in recent_reports if r.id != report.id]
        
        if not recent_reports:
            return self._create_validation(
                report.id, 'warning', 0.6,
                'No recent reports to compare against'
            )
        
        consistent_count = 0
        total_count = len(recent_reports)
        
        for other_report in recent_reports:
            if self._are_reports_consistent(report, other_report):
                consistent_count += 1
        
        consistency_ratio = consistent_count / total_count
        
        if consistency_ratio >= 0.8:
            score = 1.0
            status = 'passed'
        elif consistency_ratio >= 0.6:
            score = 0.8
            status = 'passed'
        elif consistency_ratio >= 0.4:
            score = 0.6
            status = 'warning'
        else:
            score = 0.3
            status = 'failed'
        
        return self._create_validation(
            report.id, status, score,
            f'Consistent with {consistent_count}/{total_count} recent reports'
        )
    
    def _are_reports_consistent(self, report1: UserReport, report2: UserReport) -> bool:
        """Check if two reports are consistent with each other"""
        # Same report type should have similar times
        if report1.report_type == report2.report_type:
            time_diff = abs((report1.reported_time - report2.reported_time).total_seconds() / 60)
            return time_diff <= 30  # Within 30 minutes
        
        # Different report types - check logical consistency
        if (report1.report_type == 'arrival' and report2.report_type == 'departure'):
            # Departure should be after arrival
            return report2.reported_time >= report1.reported_time
        
        return True  # Default to consistent for other combinations


class PatternValidator(BaseValidator):
    """Validates against suspicious user patterns"""
    
    def get_validation_type(self) -> str:
        return 'pattern_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        user_reliability = UserReliability.get_or_create(report.user_id)
        
        # Check user's recent reporting patterns
        patterns = self._detect_suspicious_patterns(report.user_id)
        
        if not patterns:
            return self._create_validation(
                report.id, 'passed', 0.9,
                f'No suspicious patterns detected for {user_reliability.user_type} user'
            )
        
        # Calculate score based on pattern severity
        severity_score = self._calculate_pattern_severity(patterns)
        
        if severity_score <= 0.3:
            status = 'passed'
            score = 0.8
        elif severity_score <= 0.6:
            status = 'warning'
            score = 0.6
        else:
            status = 'failed'
            score = 0.2
        
        return self._create_validation(
            report.id, status, score,
            f'Patterns detected: {", ".join(patterns)}'
        )
    
    def _detect_suspicious_patterns(self, user_id: int) -> List[str]:
        """Detect suspicious patterns in user's recent reports"""
        patterns = []
        
        # Get user's recent reports
        recent_reports = UserReport.query.filter(
            UserReport.user_id == user_id,
            UserReport.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(UserReport.created_at.desc()).all()
        
        if len(recent_reports) < 2:
            return patterns
        
        # Check for excessive negative reports
        negative_count = sum(1 for r in recent_reports if r.is_negative_report())
        if negative_count > len(recent_reports) * 0.7:  # More than 70% negative
            patterns.append('excessive_negative')
        
        # Check for impossible travel times
        for i in range(len(recent_reports) - 1):
            report1 = recent_reports[i]
            report2 = recent_reports[i + 1]
            
            if report1.station_id != report2.station_id:
                time_diff = abs((report1.reported_time - report2.reported_time).total_seconds() / 60)
                if time_diff < 10:  # Reports at different stations within 10 minutes
                    patterns.append('impossible_travel')
                    break
        
        return patterns
    
    def _calculate_pattern_severity(self, patterns: List[str]) -> float:
        """Calculate severity score based on detected patterns"""
        severity_weights = {
            'excessive_negative': 0.6,
            'impossible_travel': 0.9,
        }
        
        total_severity = sum(severity_weights.get(pattern, 0.5) for pattern in patterns)
        return min(1.0, total_severity)


class RouteValidator(BaseValidator):
    """Validates reports against known train routes"""
    
    def get_validation_type(self) -> str:
        return 'route_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        # Check if station is in the train's route
        route = Route.query.filter_by(
            train_number=report.train_number,
            station_id=report.station_id
        ).first()
        
        if route:
            return self._create_validation(
                report.id, 'passed', 1.0,
                f'Station is in train route (sequence {route.sequence_number})'
            )
        
        # Station not in official route - check if it's marked as intermediate
        if report.is_intermediate_station:
            # For intermediate stations, give moderate score
            return self._create_validation(
                report.id, 'warning', 0.6,
                'Intermediate station (not in official route)'
            )
        
        # Station not in route and not marked as intermediate
        return self._create_validation(
            report.id, 'failed', 0.1,
            'Station is not in train route'
        )


class RateLimitValidator(BaseValidator):
    """Validates against rate limiting rules"""
    
    def get_validation_type(self) -> str:
        return 'rate_limit_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        user_reliability = UserReliability.get_or_create(report.user_id)
        
        # Check if user can report
        can_report, message = user_reliability.can_report()
        if not can_report:
            return self._create_validation(
                report.id, 'failed', 0.0,
                error_message=message
            )
        
        # Check rate limits
        limits = user_reliability.get_rate_limits()
        
        # Check per-minute limit
        minute_reports = UserReport.query.filter(
            UserReport.user_id == report.user_id,
            UserReport.created_at >= datetime.utcnow() - timedelta(minutes=1)
        ).count()
        
        if minute_reports >= limits['per_minute']:
            return self._create_validation(
                report.id, 'failed', 0.0,
                f'Rate limit exceeded: {minute_reports}/{limits["per_minute"]} per minute'
            )
        
        # Check per-hour limit
        hour_reports = UserReport.query.filter(
            UserReport.user_id == report.user_id,
            UserReport.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        if hour_reports >= limits['per_hour']:
            return self._create_validation(
                report.id, 'failed', 0.0,
                f'Rate limit exceeded: {hour_reports}/{limits["per_hour"]} per hour'
            )
        
        return self._create_validation(
            report.id, 'passed', 1.0,
            f'Rate limit OK for {user_reliability.user_type} user'
        )


class DuplicateValidator(BaseValidator):
    """Validates against duplicate reports"""
    
    def get_validation_type(self) -> str:
        return 'duplicate_check'
    
    def validate(self, report: UserReport) -> ReportValidation:
        # Check for duplicate reports within time window
        duplicate = UserReport.check_duplicate(
            report.user_id, report.train_number, report.station_id, 
            report.report_type, minutes=5
        )
        
        if duplicate and duplicate.id != report.id:
            return self._create_validation(
                report.id, 'failed', 0.0,
                f'Duplicate of report {duplicate.id} within 5-minute window'
            )
        
        return self._create_validation(
            report.id, 'passed', 1.0,
            'No duplicate reports found'
        )

