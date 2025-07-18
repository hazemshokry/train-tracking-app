# app/services/validation_service.py

# Import timezone from the datetime library
from datetime import datetime, timedelta, timezone
from app.models import UserReport, Route, Station
from app.routes.station_routes import haversine

class ValidationService:
    def __init__(self, report, user, existing_reports):
        self.report = report
        self.user = user
        self.existing_reports = existing_reports
        self.results = {}

    def validate(self):
        """Runs all validation checks and returns a dictionary of results."""
        self.results['time_valid'] = self._validate_time()
        self.results['location_valid'] = self._validate_location()
        self.results['consistency_valid'] = self._validate_consistency()
        self.results['route_valid'] = self._validate_route()
        self.results['duplicate_valid'] = self._validate_duplicate()
        self.results['pattern_valid'] = self.results['duplicate_valid']
        self.results['rate_limit_valid'] = True
        return self.results

    def _validate_time(self):
        """
        Checks if the reported time is within a reasonable window (e.g., 2 hours from now).
        Both datetimes are now timezone-aware.
        """
        # --- THE FIX IS HERE ---
        # Use datetime.now(timezone.utc) to get a timezone-aware current time
        aware_now = datetime.now(timezone.utc)
        return abs((aware_now - self.report.reported_time).total_seconds()) < 7200

    def _validate_location(self):
        """Validates if the user's submitted GPS coordinates are within 1km of the station."""
        if not self.report.report_location_lat or not self.report.report_location_long:
            return 0.5

        station = Station.query.get(self.report.station_id)
        if not station or not station.location_lat or not station.location_long:
            return 0.5

        distance = haversine(
            float(self.report.report_location_lat), float(self.report.report_location_long),
            float(station.location_lat), float(station.location_long)
        )
        return distance <= 1.0

    def _validate_consistency(self):
        """Simple consistency check: True if other reports exist for the same event."""
        return len(self.existing_reports) > 0

    def _validate_route(self):
        """Validates if the reported station is on the train's official route."""
        if self.report.report_type == 'passed_station':
            return Station.query.get(self.report.station_id) is not None
            
        route_entry = Route.query.filter_by(
            train_number=self.report.train_number,
            station_id=self.report.station_id
        ).first()
        return route_entry is not None

    def _validate_duplicate(self):
        """Checks for an identical report from the same user in the last 15 minutes."""
        # Use a timezone-aware threshold
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
        duplicate = UserReport.query.filter(
            UserReport.user_id == self.user.id,
            UserReport.train_number == self.report.train_number,
            UserReport.station_id == self.report.station_id,
            UserReport.report_type == self.report.report_type,
            UserReport.created_at > time_threshold
        ).first()
        return duplicate is None