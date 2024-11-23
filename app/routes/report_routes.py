# app/routes/report_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import UserReport, Train, Station, Operation, Reward
from app.extensions import db
from datetime import datetime, timedelta, timezone

# from app.routes.user_routes import token_required  # Commented out for testing

api = Namespace('reports', description='User report related operations')

# Serializer models
report_model = api.model('UserReport', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the report'),
    'user_id': fields.Integer(description='ID of the user who submitted the report'),
    'train_number': fields.Integer(description='Train number'),
    'station_id': fields.Integer(description='Station ID'),
    'report_type': fields.String(description='Type of report', enum=['arrival', 'departure', 'onboard', 'offboard']),
    'reported_time': fields.DateTime(description='Time of the report'),
    'created_at': fields.DateTime(description='Time the report was created'),
    'is_valid': fields.Boolean(description='Validity of the report'),
})

report_create_model = api.model('UserReportCreate', {
    'train_number': fields.Integer(required=True, description='Train number'),
    'station_id': fields.Integer(required=True, description='Station ID'),
    'report_type': fields.String(required=True, description='Type of report', enum=['arrival', 'departure', 'onboard', 'offboard']),
    'reported_time': fields.DateTime(required=True, description='Time of the report in ISO 8601 format'),
})

@api.route('/me')  # User-specific reports
class UserReportList(Resource):
    # @api.doc(security='apikey')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.marshal_list_with(report_model)
    def get(self):
        """List all reports for the current user"""
        user_id = 1  # Assume user ID 1 for testing
        reports = UserReport.query.filter_by(user_id=user_id).all()
        return reports

@api.route('/')
class ReportList(Resource):
    @api.expect(report_create_model)
    @api.marshal_with(report_model, code=201)
    def post(self):
        """Create a new report and award 1 point to the user"""
        data = api.payload
        user_id = 1  # Assume user ID 1 for testing
        train_number = data['train_number']
        station_id = data['station_id']
        report_type = data['report_type']
        reported_time_str = data['reported_time']

        # Validate train_number, station_id, report_type
        train = Train.query.get(train_number)
        if not train:
            api.abort(400, 'Train not found')

        station = Station.query.get(station_id)
        if not station:
            api.abort(400, 'Station not found')

        if report_type not in ['arrival', 'departure', 'onboard', 'offboard']:
            api.abort(400, 'Invalid report type')

        # Parse reported_time from string to datetime
        try:
            reported_time = datetime.fromisoformat(reported_time_str)
        except ValueError:
            api.abort(400, 'Invalid reported_time format. Use ISO 8601 format.')

        # Determine operational date based on train's scheduled departure
        scheduled_departure_time = train.scheduled_departure_time
        operational_date = reported_time.date() if reported_time.time() >= scheduled_departure_time.time() else reported_time.date() - timedelta(days=1)

        # Fetch or create an Operation for this train and operational date
        operation = Operation.query.filter_by(train_number=train_number, operational_date=operational_date).first()
        if not operation:
            operation = Operation(
                train_number=train_number,
                operational_date=operational_date,
                status="on time"
            )
            db.session.add(operation)
            db.session.flush()  # Flush to get the operation ID without committing yet

        # Duplicate report check
        time_threshold = datetime.utcnow() - timedelta(minutes=5)
        existing_report = UserReport.query.filter(
            UserReport.user_id == user_id,
            UserReport.train_number == train_number,
            UserReport.station_id == station_id,
            UserReport.report_type == report_type,
            UserReport.reported_time > time_threshold
        ).first()
        if existing_report:
            api.abort(400, 'Duplicate report within the last 5 minutes')

        try:
            new_report = UserReport(
                user_id=user_id,
                train_number=train_number,
                operation_id=operation.id,  # Reference to the daily operation
                station_id=station_id,
                report_type=report_type,
                reported_time=reported_time,
                created_at=datetime.utcnow(),
                is_valid=True  # Assuming the report is valid upon creation
            )
            db.session.add(new_report)

            # Award 1 point to the user by creating a Reward entry
            new_reward = Reward(
                user_id=user_id,
                points=1,
                date_awarded=datetime.utcnow(),
                description='Reported a train'
            )
            db.session.add(new_reward)

            db.session.commit()
            return new_report, 201
        except Exception as e: 
            db.session.rollback()
            api.abort(500, f'Failed to create report: {str(e)}')

@api.route('/<int:id>')
@api.param('id', 'The report identifier')
class ReportResource(Resource):
    @api.marshal_with(report_model)
    def get(self, id):
        """Get a report by ID"""
        report = UserReport.query.get_or_404(id)
        return report

    @api.response(204, 'Report deleted')
    def delete(self, id):
        """Delete a report by ID"""
        report = UserReport.query.get_or_404(id)
        # ... (For now, allow deletion without authentication) ...
        db.session.delete(report)
        db.session.commit()
        return '', 204