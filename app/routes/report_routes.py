# app/routes/report_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import UserReport, User, Train, Station
from app.extensions import db
from datetime import datetime
from app.routes.user_routes import token_required

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

@api.route('/')
class ReportList(Resource):
    @api.marshal_list_with(report_model)
    def get(self):
        """List all reports (Admin only)"""
        # Assuming only admins can access this endpoint
        # Check if the current user is an admin
        # For simplicity, we'll assume user with ID 1 is admin
        # if request.current_user.id != 1:
        #     api.abort(403, 'Access forbidden')

        reports = UserReport.query.all()
        return reports

    @api.expect(report_create_model)
    @api.marshal_with(report_model, code=201)
    def post(self):
        """Create a new report"""
        data = api.payload
        # user_id = request.current_user.id
        user_id = 1
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

        new_report = UserReport(
            user_id=user_id,
            train_number=train_number,
            station_id=station_id,
            report_type=report_type,
            reported_time=reported_time,
        )
        db.session.add(new_report)
        db.session.commit()
        return new_report, 201

@api.route('/<int:id>')
@api.param('id', 'The report identifier')
class ReportResource(Resource):
    @api.marshal_with(report_model)
    def get(self, id):
        """Get a report by ID"""
        report = UserReport.query.get_or_404(id)
        # Ensure the user is accessing their own report or is admin
        # if request.current_user.id != report.user_id and request.current_user.id != 1:
        #     api.abort(403, 'Access forbidden')
        return report

    @api.response(204, 'Report deleted')
    def delete(self, id):
        """Delete a report by ID"""
        report = UserReport.query.get_or_404(id)
        # Ensure the user is deleting their own report or is admin
        if request.current_user.id != report.user_id and request.current_user.id != 1:
            api.abort(403, 'Access forbidden')
        db.session.delete(report)
        db.session.commit()
        return '', 204