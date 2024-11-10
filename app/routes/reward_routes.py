# app/routes/reward_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import Reward
from app.extensions import db
from datetime import datetime
from app.routes.user_routes import token_required

api = Namespace('rewards', description='Reward related operations')

# Serializer models
reward_model = api.model('Reward', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the reward'),
    'user_id': fields.Integer(description='ID of the user'),
    'points': fields.Integer(description='Number of reward points'),
    'date_awarded': fields.DateTime(description='Date the reward was awarded'),
    'description': fields.String(description='Description of the reward'),
})

reward_create_model = api.model('RewardCreate', {
    'points': fields.Integer(required=True, description='Number of reward points'),
    'description': fields.String(description='Description of the reward'),
})

@api.route('/')
class RewardList(Resource):
    @api.marshal_list_with(reward_model)
    def get(self):
        """List all rewards for the current user"""
        user_id = request.current_user.id
        rewards = Reward.query.filter_by(user_id=user_id).all()
        return rewards

    @api.expect(reward_create_model)
    @api.marshal_with(reward_model, code=201)
    def post(self):
        """Create a new reward for the current user"""
        data = api.payload
        user_id = request.current_user.id
        points = data['points']
        description = data.get('description')

        new_reward = Reward(
            user_id=user_id,
            points=points,
            description=description,
        )
        db.session.add(new_reward)
        db.session.commit()
        return new_reward, 201

@api.route('/<int:id>')
@api.param('id', 'The reward identifier')
class RewardResource(Resource):
    @api.marshal_with(reward_model)
    def get(self, id):
        """Get a reward by ID"""
        reward = Reward.query.get_or_404(id)
        # Ensure the user is accessing their own reward
        if request.current_user.id != reward.user_id:
            api.abort(403, 'Access forbidden')
        return reward

    @api.response(204, 'Reward deleted')
    def delete(self, id):
        """Delete a reward by ID"""
        reward = Reward.query.get_or_404(id)
        # Ensure the user is deleting their own reward
        if request.current_user.id != reward.user_id:
            api.abort(403, 'Access forbidden')

        db.session.delete(reward)
        db.session.commit()
        return '', 204