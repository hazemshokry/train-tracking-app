# app/routes/subscribe_routes.py

from flask import request
from flask_restx import Namespace, Resource
from app.models import Train, TrainSubscription
from app.extensions import db
from app.utils.auth_utils import token_required

api = Namespace('subscriptions', description='Train subscription operations')

@api.route('/<string:train_number>')
@api.param('train_number', 'The train number to subscribe/unsubscribe from')
class SubscriptionResource(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    def post(self, train_number):
        """Subscribe to a train for notifications"""
        user_id = request.current_user.id
        
        train = Train.query.get(train_number)
        if not train:
            api.abort(404, 'Train not found')
            
        existing_subscription = TrainSubscription.query.filter_by(user_id=user_id, train_number=train_number).first()
        if existing_subscription:
            return {'message': 'Already subscribed to this train'}, 200

        new_subscription = TrainSubscription(user_id=user_id, train_number=train_number)
        db.session.add(new_subscription)
        db.session.commit()
        
        return {'message': f'Successfully subscribed to train {train_number}'}, 201

    @token_required
    @api.doc(security='BearerAuth')
    def delete(self, train_number):
        """Unsubscribe from a train"""
        user_id = request.current_user.id
        
        subscription = TrainSubscription.query.filter_by(user_id=user_id, train_number=train_number).first()
        if not subscription:
            api.abort(404, 'Subscription not found')
            
        db.session.delete(subscription)
        db.session.commit()
        
        return {'message': f'Successfully unsubscribed from train {train_number}'}, 200