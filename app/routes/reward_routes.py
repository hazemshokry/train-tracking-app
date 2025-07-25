# app/routes/reward_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import Reward
from app.extensions import db
from datetime import datetime
from app.utils.auth_utils import token_required

api = Namespace('rewards', description='Reward related operations')

# Serializer models
reward_model = api.model('Reward', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the reward'),
    'user_id': fields.String(description='ID of the user'),
    'points': fields.Integer(description='Number of reward points'),
    'date_awarded': fields.DateTime(description='Date the reward was awarded'),
    'description': fields.String(description='Description of the reward'),
})

@api.route('/')
class RewardList(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.marshal_list_with(reward_model)
    def get(self):
        """List all rewards for the current user"""
        user_id = request.current_user.id
        rewards = Reward.query.filter_by(user_id=user_id).all()
        return rewards

@api.route('/<int:id>')
@api.param('id', 'The reward identifier')
class RewardResource(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.marshal_with(reward_model)
    def get(self, id):
        """Get a reward by ID"""
        reward = Reward.query.get_or_404(id)
        if reward.user_id != request.current_user.id:
            api.abort(403, 'Access forbidden')
        return reward, 200

    @token_required
    @api.doc(security='BearerAuth')
    @api.response(204, 'Reward deleted')
    def delete(self, id):
        """Delete a reward by ID"""
        reward = Reward.query.get_or_404(id)
        if reward.user_id != request.current_user.id:
            api.abort(403, 'Access forbidden')

        db.session.delete(reward)
        db.session.commit()
        return '', 204

@api.route('/total')
class TotalRewards(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    def get(self):
        """Get total reward points for the current user"""
        user_id = request.current_user.id
        total_points = db.session.query(db.func.sum(Reward.points)).filter_by(user_id=user_id).scalar() or 0
        
        return {'user_id': user_id, 'total_points': int(total_points)}, 200