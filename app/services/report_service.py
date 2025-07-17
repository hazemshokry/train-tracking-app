# Report Service - Handles all report operations
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import and_, or_, func
from app.extensions import db

from ..models.user_reports import UserReport, ReportType, ValidationStatus
from ..models.user_reliability import UserReliability
from ..models.calculated_times import CalculatedTime, TimeStatus
from ..models.report_validation import ReportValidation, ValidationSummary
from ..validators.validation_engine import ValidationEngine

class ReportService:
    """Service class for handling train report operations"""
    
    def __init__(self):
        self.validation_engine = ValidationEngine()
    
    def create_report(self, user_id: int, train_number: int, operation_id: int,
                     station_id: int, report_type: str, reported_time: datetime,
                     location_data: Dict = None, notes: str = None) -> Tuple[UserReport, ValidationSummary]:
        """Create a new train report with validation"""
        
        # Create the report object
        report = UserReport(
            user_id=user_id,
            train_number=train_number,
            operation_id=operation_id,
            station_id=station_id,
            report_type=ReportType(report_type),
            reported_time=reported_time,
            notes=notes
        )
        
        # Add location data if provided
        if location_data:
            report.reported_lat = location_data.get('lat')
            report.reported_long = location_data.get('long')
            report.location_accuracy = location_data.get('accuracy')
        
        # Check if this is an intermediate station (not in official route)
        report.is_intermediate_station = self._is_intermediate_station(train_number, station_id)
        
        # Save to get ID for validation
        db.session.add(report)
        db.session.flush()
        
        # Run validation
        validation_summary = self.validation_engine.validate_report(report)
        
        # Save validation results
        for validation in validation_summary.validations:
            db.session.add(validation)
        
        # Update user reliability based on validation
        self._update_user_reliability(user_id, validation_summary)
        
        # If report is valid, update calculated times
        if validation_summary.overall_status.value in ['passed', 'warning']:
            self._update_calculated_times(report)
        
        db.session.commit()
        
        return report, validation_summary
    
    def handle_no_show_report(self, user_id: int, train_number: int, operation_id: int,
                             station_id: int, reported_time: datetime, 
                             location_data: Dict = None) -> Tuple[UserReport, ValidationSummary]:
        """Handle a 'no show' report (train didn't arrive)"""
        
        report, validation_summary = self.create_report(
            user_id=user_id,
            train_number=train_number,
            operation_id=operation_id,
            station_id=station_id,
            report_type='no_show',
            reported_time=reported_time,
            location_data=location_data,
            notes="Train did not arrive as expected"
        )
        
        # If validated, update downstream stations
        if validation_summary.overall_status.value in ['passed', 'warning']:
            self._handle_train_cancellation(operation_id, station_id)
        
        return report, validation_summary
    
    def handle_intermediate_station_report(self, user_id: int, train_number: int, 
                                         operation_id: int, station_id: int,
                                         report_type: str, reported_time: datetime,
                                         location_data: Dict = None) -> Tuple[UserReport, ValidationSummary]:
        """Handle report from intermediate station (not in official route)"""
        
        report, validation_summary = self.create_report(
            user_id=user_id,
            train_number=train_number,
            operation_id=operation_id,
            station_id=station_id,
            report_type=report_type,
            reported_time=reported_time,
            location_data=location_data
        )
        
        # Mark as intermediate station
        report.is_intermediate_station = True
        
        # If high confidence, consider updating route estimates
        if validation_summary.weighted_score >= 0.8:
            self._update_route_estimates_from_intermediate(report)
        
        db.session.commit()
        
        return report, validation_summary
    
    def get_reports_for_train(self, train_number: int, operation_date: datetime.date,
                             station_id: int = None, limit: int = 50) -> List[UserReport]:
        """Get reports for a specific train operation"""
        
        from app.models.operations import Operation
        
        # Get operation for the date
        operation = Operation.query.filter_by(
            train_number=train_number,
            operational_date=operation_date
        ).first()
        
        if not operation:
            return []
        
        query = UserReport.query.filter_by(operation_id=operation.id)
        
        if station_id:
            query = query.filter_by(station_id=station_id)
        
        # Only return validated or pending reports
        query = query.filter(
            UserReport.validation_status.in_([
                ValidationStatus.VALIDATED, 
                ValidationStatus.PENDING
            ])
        )
        
        return query.order_by(UserReport.created_at.desc()).limit(limit).all()
    
    def get_calculated_times(self, train_number: int, operation_date: datetime.date) -> List[CalculatedTime]:
        """Get calculated times for all stations on a train route"""
        
        from app.models.operations import Operation
        
        operation = Operation.query.filter_by(
            train_number=train_number,
            operational_date=operation_date
        ).first()
        
        if not operation:
            return []
        
        return CalculatedTime.query.filter_by(
            operation_id=operation.id
        ).order_by(CalculatedTime.station_id).all()
    
    def admin_override_time(self, admin_user_id: int, operation_id: int, 
                           station_id: int, override_time: datetime, 
                           notes: str = None) -> CalculatedTime:
        """Allow admin to override calculated time"""
        
        calc_time = CalculatedTime.get_or_create(operation_id, station_id)
        calc_time.admin_override_time(admin_user_id, override_time, notes)
        
        db.session.commit()
        
        return calc_time
    
    def get_user_report_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a user's reports"""
        
        reliability = UserReliability.get_or_create(user_id)
        
        # Get recent reports
        recent_reports = UserReport.query.filter(
            UserReport.user_id == user_id,
            UserReport.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        # Calculate statistics
        total_reports = len(recent_reports)
        validated_reports = len([r for r in recent_reports if r.validation_status == ValidationStatus.VALIDATED])
        rejected_reports = len([r for r in recent_reports if r.validation_status == ValidationStatus.REJECTED])
        
        avg_confidence = sum(r.confidence_score for r in recent_reports) / total_reports if total_reports > 0 else 0
        
        return {
            'user_type': reliability.user_type,
            'reliability_score': reliability.reliability_score,
            'total_reports_30_days': total_reports,
            'validated_reports': validated_reports,
            'rejected_reports': rejected_reports,
            'average_confidence': avg_confidence,
            'rate_limits': reliability.get_rate_limits()
        }
    
    def flag_report(self, report_id: int, admin_user_id: int, reason: str) -> bool:
        """Flag a report as problematic"""
        
        report = UserReport.query.get(report_id)
        if not report:
            return False
        
        report.validation_status = ValidationStatus.FLAGGED
        report.admin_notes = reason
        report.verified_by = admin_user_id
        report.verified_at = datetime.utcnow()
        
        # Update user reliability
        reliability = UserReliability.get_or_create(report.user_id)
        reliability.update_reliability('flagged')
        
        db.session.commit()
        
        return True
    
    def approve_report(self, report_id: int, admin_user_id: int) -> bool:
        """Admin approve a report"""
        
        report = UserReport.query.get(report_id)
        if not report:
            return False
        
        report.validation_status = ValidationStatus.VALIDATED
        report.admin_verified = True
        report.verified_by = admin_user_id
        report.verified_at = datetime.utcnow()
        report.confidence_score = 1.0  # Admin approval gives max confidence
        
        # Update user reliability
        reliability = UserReliability.get_or_create(report.user_id)
        reliability.update_reliability('accurate')
        
        # Update calculated times
        self._update_calculated_times(report)
        
        db.session.commit()
        
        return True
    
    def _is_intermediate_station(self, train_number: int, station_id: int) -> bool:
        """Check if station is not in the official train route"""
        from app.models.route import Route
        
        route = Route.query.filter_by(
            train_number=train_number,
            station_id=station_id
        ).first()
        
        return route is None
    
    def _update_user_reliability(self, user_id: int, validation_summary: ValidationSummary):
        """Update user reliability based on validation results"""
        
        reliability = UserReliability.get_or_create(user_id)
        
        if validation_summary.overall_status.value == 'passed':
            reliability.update_reliability('accurate')
        elif validation_summary.overall_status.value == 'failed':
            # Check if it's spam or just inaccurate
            if any('spam' in reason.lower() or 'duplicate' in reason.lower() 
                   for reason in validation_summary.get_failure_reasons()):
                reliability.update_reliability('spam')
            else:
                reliability.update_reliability('flagged')
    
    def _update_calculated_times(self, report: UserReport):
        """Update calculated times based on new report"""
        
        calc_time = CalculatedTime.get_or_create(report.operation_id, report.station_id)
        
        # Get all valid reports for this station
        valid_reports = UserReport.query.filter(
            UserReport.operation_id == report.operation_id,
            UserReport.station_id == report.station_id,
            UserReport.validation_status.in_([
                ValidationStatus.VALIDATED,
                ValidationStatus.PENDING
            ])
        ).all()
        
        # Update calculated time
        calc_time.update_from_reports(valid_reports)
    
    def _handle_train_cancellation(self, operation_id: int, cancelled_station_id: int):
        """Handle train cancellation at a station - update downstream stations"""
        
        from app.models.route import Route
        from app.models.operations import Operation
        
        operation = Operation.query.get(operation_id)
        if not operation:
            return
        
        # Get the cancelled station's sequence number
        cancelled_route = Route.query.filter_by(
            train_number=operation.train_number,
            station_id=cancelled_station_id
        ).first()
        
        if not cancelled_route:
            return
        
        # Get all downstream stations
        downstream_routes = Route.query.filter(
            Route.train_number == operation.train_number,
            Route.sequence_number > cancelled_route.sequence_number
        ).all()
        
        # Update calculated times for downstream stations
        for route in downstream_routes:
            calc_time = CalculatedTime.get_or_create(operation_id, route.station_id)
            calc_time.status = TimeStatus.CANCELLED
            calc_time.confidence_level = 0.9  # High confidence in cancellation
    
    def _update_route_estimates_from_intermediate(self, report: UserReport):
        """Update route estimates based on intermediate station report"""
        
        # This would involve complex logic to estimate times for official stations
        # based on intermediate station reports. For now, we'll log it for analysis.
        
        # In a full implementation, this would:
        # 1. Find nearby official stations
        # 2. Estimate travel times based on distance/historical data
        # 3. Update calculated times for those stations
        
        pass
    
    def get_train_status_summary(self, train_number: int, operation_date: datetime.date) -> Dict[str, Any]:
        """Get comprehensive status summary for a train"""
        
        from app.models.operations import Operation
        
        operation = Operation.query.filter_by(
            train_number=train_number,
            operational_date=operation_date
        ).first()
        
        if not operation:
            return {'error': 'Operation not found'}
        
        # Get calculated times
        calc_times = self.get_calculated_times(train_number, operation_date)
        
        # Get recent reports
        recent_reports = UserReport.query.filter(
            UserReport.operation_id == operation.id,
            UserReport.created_at >= datetime.utcnow() - timedelta(hours=6)
        ).order_by(UserReport.created_at.desc()).all()
        
        # Calculate summary statistics
        total_reports = len(recent_reports)
        validated_reports = len([r for r in recent_reports if r.validation_status == ValidationStatus.VALIDATED])
        
        # Find last reported station
        last_report = recent_reports[0] if recent_reports else None
        
        # Calculate overall delay
        avg_delay = sum(ct.delay_minutes for ct in calc_times) / len(calc_times) if calc_times else 0
        
        return {
            'train_number': train_number,
            'operation_date': operation_date.isoformat(),
            'operation_status': operation.status,
            'total_delay_minutes': operation.total_delay,
            'average_delay_minutes': int(avg_delay),
            'total_reports_6h': total_reports,
            'validated_reports': validated_reports,
            'last_reported_station': {
                'station_id': last_report.station_id,
                'report_type': last_report.report_type.value,
                'reported_time': last_report.reported_time.isoformat(),
                'confidence': last_report.confidence_score
            } if last_report else None,
            'station_times': [ct.to_dict() for ct in calc_times]
        }

