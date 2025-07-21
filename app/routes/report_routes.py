# app/routes/report_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import UserReport, Train, Station, Operation, Reward, User
from app.extensions import db
from datetime import datetime, timedelta

# Import the new services
from app.services.validation_service import ValidationService
from app.services.scoring_service import ScoringService

# Assuming token_required is properly set up for authentication
# from app.utils.auth_utils import token_required

api = Namespace('reports', description='User report related operations')

# --- API Models ---

# Model for displaying a report
report_model = api.model('UserReport', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the report'),
    'user_id': fields.String(description='ID of the user who submitted the report'),
    'train_number': fields.String(description='Train number'),
    'station_id': fields.Integer(description='Station ID'),
    'report_type': fields.String(description='Type of report', enum=['arrival', 'departure', 'onboard', 'offboard', 'delay', 'cancelled', 'passed_station']),
    'reported_time': fields.DateTime(description='Time of the report'),
    'created_at': fields.DateTime(description='Time the report was created'),
    'is_valid': fields.Boolean(description='Validity of the report based on confidence score'),
    'confidence_score': fields.Float(description='Calculated confidence score for the report')
})

# Model for creating a new report
report_create_model = api.model('UserReportCreate', {
    'train_number': fields.String(required=True, description='Train number'),
    'station_id': fields.Integer(required=True, description='Station ID'),
    'report_type': fields.String(required=True, description='Type of report', enum=['arrival', 'departure', 'onboard', 'offboard', 'delay', 'cancelled', 'passed_station']),
    'reported_time': fields.DateTime(required=True, description='Time of the report in ISO 8601 format'),
    'latitude': fields.Float(description='User\'s current latitude for location validation'),
    'longitude': fields.Float(description='User\'s current longitude for location validation'),
})

# Model for the response after creating a report
report_response_model = api.model('UserReportResponse', {
    'message': fields.String(description='Status message'),
    'confidence_score': fields.Float(description='The calculated confidence score of the report'),
    'report_id': fields.Integer(description='The ID of the created report')
})

# --- Report Endpoints ---

@api.route('/me')
class UserReportList(Resource):
    # @token_required # Uncomment when auth is ready
    @api.marshal_list_with(report_model)
    def get(self):
        """List all reports for the current user"""
        # user_id = request.current_user.id # Use this in production
        user_id = 1  # Assume user ID 1 for testing
        reports = UserReport.query.filter_by(user_id=user_id).order_by(UserReport.created_at.desc()).all()
        return reports

@api.route('/')
class ReportList(Resource):
    # @token_required # Uncomment when auth is ready
    @api.expect(report_create_model)
    @api.marshal_with(report_response_model, code=201)
    def post(self):
        """
        Creates, validates, and scores a new user report.
        It assesses the report's quality and rewards the user accordingly.
        """
        data = api.payload
        # user = request.current_user # Use this in production
        user = User.query.get(1) # For testing
        
        if not user:
            api.abort(401, 'User not found or not authenticated.')

        # 1. Basic Validation
        if not Train.query.get(data['train_number']):
            api.abort(404, f"Train with number {data['train_number']} not found.")
        if not Station.query.get(data['station_id']):
            api.abort(404, f"Station with ID {data['station_id']} not found.")
        try:
            reported_time = datetime.fromisoformat(data['reported_time'].replace('Z', '+00:00'))
        except ValueError:
            api.abort(400, 'Invalid reported_time format. Please use ISO 8601.')

        # 2. Advanced Validation & Scoring
        new_report = UserReport(
            user_id=user.id, train_number=data['train_number'], station_id=data['station_id'],
            report_type=data['report_type'], reported_time=reported_time,
            report_location_lat=data.get('latitude'), report_location_long=data.get('longitude')
        )
        existing = UserReport.query.filter_by(train_number=new_report.train_number, station_id=new_report.station_id).all()
        
        validator = ValidationService(new_report, user, existing)
        validation_results = validator.validate()

        if not validation_results['duplicate_valid']:
            api.abort(409, 'Duplicate report: A similar report was submitted by you recently.')

        scorer = ScoringService(validation_results, user)
        confidence_score = scorer.calculate_score()
        new_report.confidence_score = confidence_score
        new_report.is_valid = confidence_score > 0.4

        # 3. Database Commit
        operation = Operation.query.filter_by(train_number=data['train_number'], operational_date=reported_time.date()).first()
        if not operation:
            operation = Operation(train_number=data['train_number'], operational_date=reported_time.date())
            db.session.add(operation)
            db.session.flush()

        new_report.operation_id = operation.id
        db.session.add(new_report)

        if new_report.is_valid:
            points = round(confidence_score * 10)
            if points > 0:
                reward = Reward(user_id=user.id, points=points, description=f"Report ({points} pts) for train {data['train_number']}")
                db.session.add(reward)

        db.session.commit()
        
        return {
            'message': 'Report processed successfully.',
            'confidence_score': confidence_score,
            'report_id': new_report.id
        }, 201

@api.route('/<int:id>')
@api.param('id', 'The report identifier')
class ReportResource(Resource):
    # @token_required # Uncomment when auth is ready
    @api.marshal_with(report_model)
    def get(self, id):
        """Get a specific report by its ID"""
        report = UserReport.query.get_or_404(id)
        # Add logic here to ensure user can only access their own reports if needed
        return report

    # @token_required # Uncomment when auth is ready
    @api.response(204, 'Report deleted successfully')
    def delete(self, id):
        """Delete a report by its ID"""
        report = UserReport.query.get_or_404(id)
        # Add logic here to ensure user can only delete their own reports
        # current_user_id = request.current_user.id
        current_user_id = 1 # for testing
        if report.user_id != current_user_id:
            api.abort(403, "You are not authorized to delete this report.")
            
        db.session.delete(report)
        db.session.commit()
        return '', 204