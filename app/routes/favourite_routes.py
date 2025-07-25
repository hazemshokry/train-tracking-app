# app/routes/favourite_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.train import Train
from app.models.train_subscription import TrainSubscription
from app.extensions import db
from app.utils.auth_utils import token_required
from app.routes.train_routes import serialize_train, train_summary_model # Import serialize_train and train_summary_model

api = Namespace('favourites', description='Favourite trains related operations')

# New model that includes train summary and added_at field
favourite_train_details_model = api.inherit('FavouriteTrainDetails', train_summary_model, {
    'added_at': fields.DateTime(description='Date and time the train was added to favourites'),
})

favourite_train_create_model = api.model('FavouriteTrainCreate', {
    'train_number': fields.String(required=True, description='Train number'),
})

@api.route('/')
class FavouriteTrainList(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.marshal_list_with(favourite_train_details_model) # Use the new combined model
    def get(self):
        """List all favourite trains for the current user"""
        user_id = request.current_user.id
        favourite_trains = UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        favourite_train_numbers = [fav.train_number for fav in favourite_trains]
        
        subscribed_train_numbers = [sub.train_number for sub in TrainSubscription.query.filter_by(user_id=user_id).all()]

        train_list = []
        for fav in favourite_trains:
            train = fav.train
            train_details = serialize_train(train, favourite_train_numbers, subscribed_train_numbers, include_stations=False)
            train_details['added_at'] = fav.added_at # Add the added_at field
            train_list.append(train_details)

        return train_list, 200

    @token_required
    @api.doc(security='BearerAuth')
    @api.expect(favourite_train_create_model)
    @api.marshal_with(favourite_train_details_model, code=201)
    def post(self):
        """Add a train to the user's favourites"""
        data = api.payload
        user_id = request.current_user.id
        train_number = data['train_number']

        train = Train.query.filter_by(train_number=train_number).first()
        if not train:
            api.abort(404, 'Train not found')

        existing_favourite = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if existing_favourite:
            api.abort(400, 'Train already in favourites')

        new_favourite = UserFavouriteTrain(
            user_id=user_id,
            train_number=train_number,
        )
        db.session.add(new_favourite)
        db.session.commit()
        
        favourite_train_numbers = [fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()]
        subscribed_train_numbers = [sub.train_number for sub in TrainSubscription.query.filter_by(user_id=user_id).all()]
        
        train_details = serialize_train(new_favourite.train, favourite_train_numbers, subscribed_train_numbers, include_stations=False)
        train_details['added_at'] = new_favourite.added_at
        
        return train_details, 201
    
    @token_required
    @api.doc(security='BearerAuth')
    @api.response(200, 'All favourite trains deleted successfully')
    def delete(self):
        """Delete all favourite trains for the current user"""
        user_id = request.current_user.id
        
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
    @token_required
    @api.doc(security='BearerAuth')
    def delete(self, train_number):
        """Remove a train from the user's favourites"""
        user_id = request.current_user.id

        favourite_train = UserFavouriteTrain.query.filter_by(user_id=user_id, train_number=train_number).first()
        if not favourite_train:
            api.abort(404, 'Train not found in favourites')

        db.session.delete(favourite_train)
        db.session.commit()

        return {'message': 'Train removed from favourites'}, 200