# app/routes/favourite_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.train import Train
from app.extensions import db
# from app.utils.auth_util import token_required  # Keep this import commented out for testing

api = Namespace('favourites', description='Favourite trains related operations')

# Serializer models
favourite_train_model = api.model('FavouriteTrain', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the favourite train entry'),
    'user_id': fields.String(description='The user ID of the user who favourited the train'),
    'train_number': fields.String(description='Train number'),
    'added_at': fields.DateTime(description='Date and time the train was added to favourites'),
    # 'notification_enabled': fields.Boolean(description='Whether notifications are enabled for this train'),
})

favourite_train_create_model = api.model('FavouriteTrainCreate', {
    'train_number': fields.String(required=True, description='Train number'),
    # 'notification_enabled': fields.Boolean(description='Enable notifications', default=False),
})

@api.route('/')
class FavouriteTrainList(Resource):
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.marshal_list_with(favourite_train_model)
    def get(self):
        """List all favourite trains for the current user"""
        # user_id = request.current_user.id
        user_id = 'a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e'  # Hardcoded user ID for testing
        favourite_trains = UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        return favourite_trains, 200

    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.expect(favourite_train_create_model)
    @api.marshal_with(favourite_train_model, code=201)
    def post(self):
        """Add a train to the user's favourites"""
        data = api.payload
        # user_id = request.current_user.id
        user_id = 'a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e'  # Hardcoded user ID for testing
        train_number = data['train_number']
        # notification_enabled = data.get('notification_enabled', False)

        # Validate train_number
        train = Train.query.filter_by(train_number=train_number).first()
        if not train:
            api.abort(404, 'Train not found')

        # Check if the train is already in favourites
        existing_favourite = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if existing_favourite:
            api.abort(400, 'Train already in favourites')

        new_favourite = UserFavouriteTrain(
            user_id=user_id,
            train_number=train_number,
            # notification_enabled=notification_enabled,
        )
        db.session.add(new_favourite)
        db.session.commit()

        return new_favourite, 201
    
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.response(200, 'All favourite trains deleted successfully')
    def delete(self):
        """Delete all favourite trains for the current user"""
        # user_id = request.current_user.id
        user_id = 'a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e'  # Hardcoded user ID for testing
        
        # Find all favourite train entries for the user
        favourite_trains = UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        
        if not favourite_trains:
            return {'message': 'No favourite trains to delete'}, 200

        for favourite in favourite_trains:
            db.session.delete(favourite)
        
        db.session.commit()

        return {'message': 'All favourite trains deleted successfully'}, 200

@api.route('/<string:train_number>')
@api.param('train_number', 'The train number')
class FavouriteTrainResource(Resource):
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    def delete(self, train_number):
        """Remove a train from the user's favourites"""
        # user_id = request.current_user.id
        user_id = 'a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e'  # Hardcoded user ID for testing

        # Find the favourite train entry
        favourite_train = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if not favourite_train:
            api.abort(404, 'Train not found in favourites')

        db.session.delete(favourite_train)
        db.session.commit()

        return {'message': 'Train removed from favourites'}, 200
