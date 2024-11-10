# app/routes/favourite_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.train import Train
from app.extensions import db
from app.routes.user_routes import token_required

api = Namespace('favourites', description='Favourite trains related operations')

# Serializer models
favourite_train_model = api.model('FavouriteTrain', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the favourite train entry'),
    'user_id': fields.Integer(description='ID of the user'),
    'train_number': fields.Integer(description='Train number'),
    'added_at': fields.DateTime(description='Date and time the train was added to favourites'),
})

favourite_train_create_model = api.model('FavouriteTrainCreate', {
    'train_number': fields.Integer(required=True, description='Train number'),
    'notification_enabled': fields.Boolean(required=True, description='Whether notifications are enabled for this train'),
})

@api.route('/')
class FavouriteTrainList(Resource):
    @api.marshal_list_with(favourite_train_model)
    # @token_required
    def get(self):
        """List all favourite trains for the current user"""
        # user_id = request.current_user.id
        user_id = 1
        favourite_trains = UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        return favourite_trains

    @api.expect(favourite_train_create_model)
    @api.marshal_with(favourite_train_model, code=201)
    # @token_required
    def post(self):
        """Add a train to the user's favourites"""
        data = api.payload
        user_id = request.current_user.id
        train_number = data['train_number']
        notification_enabled = data['notification_enabled']

        # Validate train_number
        train = Train.query.get(train_number)
        if not train:
            api.abort(400, 'Train not found')

        # Check if the train is already in favourites
        existing_favourite = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if existing_favourite:
            api.abort(400, 'Train already in favourites')

        new_favourite = UserFavouriteTrain(
            user_id=user_id,
            train_number=train_number,
        )
        db.session.add(new_favourite)
        db.session.commit()

        # Update notification settings (assuming you have a model for this)
        # ...

        return new_favourite, 201

@api.route('/<int:train_number>')
@api.param('train_number', 'The train number')
class FavouriteTrainResource(Resource):
    @api.marshal_with(favourite_train_model)
    # @token_required
    def delete(self, train_number):
        """Remove a train from the user's favourites"""
        user_id = request.current_user.id

        # Find the favourite train entry
        favourite_train = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if not favourite_train:
            api.abort(404, 'Train not found in favourites')

        db.session.delete(favourite_train)
        db.session.commit()

        # Update notification settings (assuming you have a model for this)
        # ...

        return '', 204