from flask import request, current_app as app
from flask_restx import Namespace, Resource
from app.extensions import db
from app.synthetic_data import insert_synthetic_data  # Import the function from your main script
from app.models import Train  # Ensure Train model is available for validation

# Define a new namespace for synthetic data operations
api = Namespace('synthetic', description='Synthetic data generation operations')

@api.route('/generate-synthetic-data')
class GenerateSyntheticData(Resource):
    @api.param('num_reports', 'Number of synthetic reports to generate', default=10)
    @api.param('train_number', 'Specific train number to filter (optional)')
    @api.param('user_id', 'Specific user ID to filter (optional)')
    def post(self):
        """Generate synthetic data for user reports."""
        try:
            # Retrieve parameters from the request, defaulting num_reports to 10 if not provided
            num_reports = int(request.args.get('num_reports', 10))
            train_number = request.args.get('train_number')
            user_id = request.args.get('user_id')

            # Validate train_number if provided
            if train_number:
                train_exists = db.session.query(Train).filter_by(train_number=train_number).first()
                if not train_exists:
                    return {'error': f'Train number {train_number} does not exist.'}, 400

            # Call the insert_synthetic_data function with app context
            insert_synthetic_data(app, num_reports=num_reports, train_number=train_number, user_id=user_id)
            return {'message': 'Synthetic data generated successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500