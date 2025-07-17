# Report Validation Engine
from datetime import datetime, timedelta
import math
from typing import List, Dict, Any, Tuple
from ..models.report_validation import (
    ReportValidation, ValidationType, ValidationResult, ValidationSummary
)
from ..models.user_reports import UserReport
from ..models.user_reliability import UserReliability

class ValidationEngine:
    """Main validation engine that orchestrates all validation checks"""
    
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
    
    def validate_report(self, report: UserReport) -> ValidationSummary:
        """Run all validations on a report and return summary"""
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
                    status=ValidationResult.FAILED,
                    score=0.0,
                    error_message=f"Validation error: {str(e)}",
                    processed_by=validator.__class__.__name__
                )
                validations.append(error_validation)
        
        # Create summary
        summary = ValidationSummary(validations)
        
        # Update report with validation results
        report.update_confidence_score(validations)
        
        return summary


class BaseValidator:
    """Base class for all validators"""
    
    def get_validation_type(self) -> ValidationType:
        """Return the validation type this validator handles"""
        raise NotImplementedError
    
    def validate(self, report: UserReport) -> ReportValidation:
        """Validate a report and return validation result"""
        raise NotImplementedError
    
    def _create_validation(self, report_id: int, status: ValidationResult, 
                          score: float, details: Dict = None, 
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
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.TIME_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        now = datetime.utcnow()
        report_time = report.reported_time
        
        # Check if report time is reasonable
        if report_time > now + timedelta(hours=2):
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.0,
                {'reason': 'future_time', 'hours_ahead': (report_time - now).total_seconds() / 3600},
                'Report time is too far in the future'
            )
        
        if report_time < now - timedelta(days=2):
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.1,
                {'reason': 'old_time', 'days_old': (now - report_time).days},
                'Report time is too old'
            )
        
        # Get scheduled time for comparison
        scheduled_time = self._get_scheduled_time(report)
        if scheduled_time:
            score = report.calculate_time_score(scheduled_time)
            time_diff_minutes = abs((report_time - scheduled_time).total_seconds() / 60)
            
            if score >= 0.8:
                status = ValidationResult.PASSED
            elif score >= 0.5:
                status = ValidationResult.WARNING
            else:
                status = ValidationResult.FAILED
            
            return self._create_validation(
                report.id, status, score,
                {
                    'scheduled_time': scheduled_time.isoformat(),
                    'time_difference_minutes': time_diff_minutes,
                    'expected_window': report.get_expected_time_window()
                }
            )
        
        # No scheduled time available - neutral score
        return self._create_validation(
            report.id, ValidationResult.WARNING, 0.6,
            {'reason': 'no_scheduled_time'},
            'No scheduled time available for comparison'
        )
    
    def _get_scheduled_time(self, report: UserReport) -> datetime:
        """Get scheduled time for the report's station and train"""
        from app.models.route import Route
        
        route = Route.query.filter_by(
            train_number=report.train_number,
            station_id=report.station_id
        ).first()
        
        if not route:
            return None
        
        operation_date = report.operation.operational_date
        
        if report.report_type.value in ['arrival', 'early_arrival'] and route.scheduled_arrival_time:
            return datetime.combine(operation_date, route.scheduled_arrival_time)
        elif report.report_type.value == 'departure' and route.scheduled_departure_time:
            return datetime.combine(operation_date, route.scheduled_departure_time)
        
        return None


class LocationValidator(BaseValidator):
    """Validates report location against station coordinates"""
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.LOCATION_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        if not report.reported_lat or not report.reported_long:
            return self._create_validation(
                report.id, ValidationResult.WARNING, 0.5,
                {'reason': 'no_gps'},
                'No GPS coordinates provided'
            )
        
        station = report.station
        if not station.location_lat or not station.location_long:
            return self._create_validation(
                report.id, ValidationResult.WARNING, 0.6,
                {'reason': 'no_station_coords'},
                'Station coordinates not available'
            )
        
        # Calculate distance
        distance_km = self._calculate_distance(
            float(report.reported_lat), float(report.reported_long),
            float(station.location_lat), float(station.location_long)
        )
        
        # Score based on distance and report type
        score = self._calculate_location_score(distance_km, report.report_type.value)
        
        if score >= 0.8:
            status = ValidationResult.PASSED
        elif score >= 0.5:
            status = ValidationResult.WARNING
        else:
            status = ValidationResult.FAILED
        
        return self._create_validation(
            report.id, status, score,
            {
                'distance_km': distance_km,
                'station_coords': [float(station.location_lat), float(station.location_long)],
                'report_coords': [float(report.reported_lat), float(report.reported_long)],
                'accuracy_meters': report.location_accuracy
            }
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
        # Different report types have different acceptable distances
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
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.CONSISTENCY_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        # Get recent reports for the same train and station
        recent_reports = self._get_recent_reports(report)
        
        if not recent_reports:
            return self._create_validation(
                report.id, ValidationResult.WARNING, 0.6,
                {'reason': 'no_recent_reports'},
                'No recent reports to compare against'
            )
        
        consistent_count = 0
        total_count = len(recent_reports)
        time_differences = []
        
        for other_report in recent_reports:
            if self._are_reports_consistent(report, other_report):
                consistent_count += 1
            
            # Track time differences
            time_diff = abs((report.reported_time - other_report.reported_time).total_seconds() / 60)
            time_differences.append(time_diff)
        
        consistency_ratio = consistent_count / total_count
        avg_time_diff = sum(time_differences) / len(time_differences) if time_differences else 0
        
        # Calculate score
        if consistency_ratio >= 0.8:
            score = 1.0
            status = ValidationResult.PASSED
        elif consistency_ratio >= 0.6:
            score = 0.8
            status = ValidationResult.PASSED
        elif consistency_ratio >= 0.4:
            score = 0.6
            status = ValidationResult.WARNING
        else:
            score = 0.3
            status = ValidationResult.FAILED
        
        return self._create_validation(
            report.id, status, score,
            {
                'consistent_reports': consistent_count,
                'total_reports': total_count,
                'consistency_ratio': consistency_ratio,
                'avg_time_difference_minutes': avg_time_diff
            }
        )
    
    def _get_recent_reports(self, report: UserReport) -> List[UserReport]:
        """Get recent reports for the same train and station"""
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        return UserReport.query.filter(
            UserReport.train_number == report.train_number,
            UserReport.station_id == report.station_id,
            UserReport.created_at >= cutoff_time,
            UserReport.id != report.id,
            UserReport.validation_status != ValidationResult.REJECTED
        ).order_by(UserReport.created_at.desc()).limit(10).all()
    
    def _are_reports_consistent(self, report1: UserReport, report2: UserReport) -> bool:
        """Check if two reports are consistent with each other"""
        # Same report type should have similar times
        if report1.report_type == report2.report_type:
            time_diff = abs((report1.reported_time - report2.reported_time).total_seconds() / 60)
            return time_diff <= 30  # Within 30 minutes
        
        # Different report types - check logical consistency
        if (report1.report_type.value == 'arrival' and report2.report_type.value == 'departure'):
            # Departure should be after arrival
            return report2.reported_time >= report1.reported_time
        
        return True  # Default to consistent for other combinations


class PatternValidator(BaseValidator):
    """Validates against suspicious user patterns"""
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.PATTERN_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        user_reliability = UserReliability.get_or_create(report.user_id)
        
        # Check user's recent reporting patterns
        patterns = self._detect_suspicious_patterns(report.user_id)
        
        if not patterns:
            return self._create_validation(
                report.id, ValidationResult.PASSED, 0.9,
                {'user_type': user_reliability.user_type},
                'No suspicious patterns detected'
            )
        
        # Calculate score based on pattern severity
        severity_score = self._calculate_pattern_severity(patterns)
        
        if severity_score <= 0.3:
            status = ValidationResult.PASSED
            score = 0.8
        elif severity_score <= 0.6:
            status = ValidationResult.WARNING
            score = 0.6
        else:
            status = ValidationResult.FAILED
            score = 0.2
        
        return self._create_validation(
            report.id, status, score,
            {
                'patterns_detected': patterns,
                'severity_score': severity_score,
                'user_reliability_score': user_reliability.reliability_score
            }
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
        
        # Check for identical reports
        if self._has_identical_reports(recent_reports):
            patterns.append('identical_reports')
        
        # Check for impossible travel times
        if self._has_impossible_travel_times(recent_reports):
            patterns.append('impossible_travel')
        
        # Check for excessive negative reports
        if self._has_excessive_negative_reports(recent_reports):
            patterns.append('excessive_negative')
        
        # Check for bot-like timing
        if self._has_bot_timing_patterns(recent_reports):
            patterns.append('bot_timing')
        
        return patterns
    
    def _has_identical_reports(self, reports: List[UserReport]) -> bool:
        """Check for identical reports"""
        seen = set()
        for report in reports:
            key = (report.train_number, report.station_id, report.report_type, 
                   report.reported_time.replace(second=0, microsecond=0))
            if key in seen:
                return True
            seen.add(key)
        return False
    
    def _has_impossible_travel_times(self, reports: List[UserReport]) -> bool:
        """Check for impossible travel times between reports"""
        for i in range(len(reports) - 1):
            report1 = reports[i]
            report2 = reports[i + 1]
            
            # Skip if same station
            if report1.station_id == report2.station_id:
                continue
            
            time_diff = abs((report1.reported_time - report2.reported_time).total_seconds() / 60)
            
            # If reports are within 10 minutes but at different stations
            if time_diff < 10:
                return True
        
        return False
    
    def _has_excessive_negative_reports(self, reports: List[UserReport]) -> bool:
        """Check for excessive negative reports"""
        negative_count = sum(1 for r in reports if r.is_negative_report())
        return negative_count > len(reports) * 0.7  # More than 70% negative
    
    def _has_bot_timing_patterns(self, reports: List[UserReport]) -> bool:
        """Check for bot-like timing patterns"""
        if len(reports) < 5:
            return False
        
        # Check for reports at exact intervals
        intervals = []
        for i in range(len(reports) - 1):
            interval = (reports[i].created_at - reports[i + 1].created_at).total_seconds()
            intervals.append(interval)
        
        # Check if intervals are suspiciously regular
        if len(set(intervals)) == 1:  # All intervals identical
            return True
        
        return False
    
    def _calculate_pattern_severity(self, patterns: List[str]) -> float:
        """Calculate severity score based on detected patterns"""
        severity_weights = {
            'identical_reports': 0.8,
            'impossible_travel': 0.9,
            'excessive_negative': 0.6,
            'bot_timing': 0.7
        }
        
        total_severity = sum(severity_weights.get(pattern, 0.5) for pattern in patterns)
        return min(1.0, total_severity)


class RouteValidator(BaseValidator):
    """Validates reports against known train routes"""
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.ROUTE_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        from app.models.route import Route
        
        # Check if station is in the train's route
        route = Route.query.filter_by(
            train_number=report.train_number,
            station_id=report.station_id
        ).first()
        
        if route:
            return self._create_validation(
                report.id, ValidationResult.PASSED, 1.0,
                {'route_sequence': route.sequence_number},
                'Station is in train route'
            )
        
        # Station not in official route - check if it's reasonable
        if report.is_intermediate_station:
            # For intermediate stations, check if it's geographically reasonable
            score = self._validate_intermediate_station(report)
            
            if score >= 0.7:
                status = ValidationResult.PASSED
            elif score >= 0.5:
                status = ValidationResult.WARNING
            else:
                status = ValidationResult.FAILED
            
            return self._create_validation(
                report.id, status, score,
                {'intermediate_station': True},
                'Intermediate station validation'
            )
        
        # Station not in route and not marked as intermediate
        return self._create_validation(
            report.id, ValidationResult.FAILED, 0.1,
            {'reason': 'station_not_in_route'},
            'Station is not in train route'
        )
    
    def _validate_intermediate_station(self, report: UserReport) -> float:
        """Validate intermediate station reports"""
        # This would involve checking if the station is geographically
        # between known route stations, checking historical data, etc.
        # For now, return a moderate score
        return 0.6


class RateLimitValidator(BaseValidator):
    """Validates against rate limiting rules"""
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.RATE_LIMIT_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        user_reliability = UserReliability.get_or_create(report.user_id)
        
        # Check if user can report
        can_report, message = user_reliability.can_report()
        if not can_report:
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.0,
                {'reason': 'user_blocked'},
                message
            )
        
        # Check rate limits
        limits = user_reliability.get_rate_limits()
        recent_reports = self._get_user_recent_reports(report.user_id)
        
        # Check per-minute limit
        minute_reports = [r for r in recent_reports 
                         if r.created_at > datetime.utcnow() - timedelta(minutes=1)]
        if len(minute_reports) >= limits['per_minute']:
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.0,
                {'limit_type': 'per_minute', 'count': len(minute_reports), 'limit': limits['per_minute']},
                'Rate limit exceeded: too many reports per minute'
            )
        
        # Check per-hour limit
        hour_reports = [r for r in recent_reports 
                       if r.created_at > datetime.utcnow() - timedelta(hours=1)]
        if len(hour_reports) >= limits['per_hour']:
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.0,
                {'limit_type': 'per_hour', 'count': len(hour_reports), 'limit': limits['per_hour']},
                'Rate limit exceeded: too many reports per hour'
            )
        
        return self._create_validation(
            report.id, ValidationResult.PASSED, 1.0,
            {'user_type': user_reliability.user_type},
            'Rate limit check passed'
        )
    
    def _get_user_recent_reports(self, user_id: int) -> List[UserReport]:
        """Get user's recent reports for rate limiting"""
        return UserReport.query.filter(
            UserReport.user_id == user_id,
            UserReport.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).all()


class DuplicateValidator(BaseValidator):
    """Validates against duplicate reports"""
    
    def get_validation_type(self) -> ValidationType:
        return ValidationType.DUPLICATE_CHECK
    
    def validate(self, report: UserReport) -> ReportValidation:
        # Check for duplicate reports within time window
        time_threshold = datetime.utcnow() - timedelta(minutes=5)
        
        duplicate = UserReport.query.filter(
            UserReport.user_id == report.user_id,
            UserReport.train_number == report.train_number,
            UserReport.station_id == report.station_id,
            UserReport.report_type == report.report_type,
            UserReport.created_at > time_threshold,
            UserReport.id != report.id
        ).first()
        
        if duplicate:
            return self._create_validation(
                report.id, ValidationResult.FAILED, 0.0,
                {'duplicate_report_id': duplicate.id, 'time_window_minutes': 5},
                'Duplicate report within 5-minute window'
            )
        
        return self._create_validation(
            report.id, ValidationResult.PASSED, 1.0,
            {},
            'No duplicate reports found'
        )

