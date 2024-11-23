# app/routes/reward_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import Reward
from app.extensions import db
from datetime import datetime
# from app.routes.user_routes import token_required  # Commented out for testing

api = Namespace('rewards', description='Reward related operations')

# Serializer models
reward_model = api.model('Reward', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the reward'),
    'user_id': fields.Integer(description='ID of the user'),
    'points': fields.Integer(description='Number of reward points'),
    'date_awarded': fields.DateTime(description='Date the reward was awarded'),
    'description': fields.String(description='Description of the reward'),
})

# Remove or restrict the create model if rewards are auto-generated
# reward_create_model = api.model('RewardCreate', {
#     'points': fields.Integer(required=True, description='Number of reward points'),
#     'description': fields.String(description='Description of the reward'),
# })

@api.route('/')
class RewardList(Resource):
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.marshal_list_with(reward_model)
    def get(self):
        """List all rewards for the current user"""
        user_id = 1  # Assume user ID 1 for testing
        rewards = Reward.query.filter_by(user_id=user_id).all()
        return rewards

# Optionally, remove the POST endpoint for regular users
# If you decide to keep it for admin purposes, ensure proper authentication and authorization
# @api.route('/')
# class RewardList(Resource):
#     @api.expect(reward_create_model)
#     @api.marshal_with(reward_model, code=201)
#     def post(self):
#         """Create a new reward"""
#         data = api.payload
#         user_id = request.current_user.id
#         points = data['points']
#         description = data.get('description')

#         new_reward = Reward(
#             user_id=user_id,
#             points=points,
#             description=description,
#             date_awarded=datetime.utcnow()
#         )
#         db.session.add(new_reward)
#         db.session.commit()
#         return new_reward, 201

@api.route('/<int:id>')
@api.param('id', 'The reward identifier')
class RewardResource(Resource):
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    @api.marshal_with(reward_model)
    def get(self, id):
        """Get a reward by ID"""
        reward = Reward.query.get_or_404(id)
        # Ensure the user is accessing their own reward
        if reward.user_id != 1:  # Replace with `request.current_user.id` in production
            api.abort(403, 'Access forbidden')
        return reward, 200

    @api.response(204, 'Reward deleted')
    def delete(self, id):
        """Delete a reward by ID"""
        reward = Reward.query.get_or_404(id)
        # Ensure the user is deleting their own reward
        if reward.user_id != 1:  # Replace with `request.current_user.id` in production
            api.abort(403, 'Access forbidden')

        db.session.delete(reward)
        db.session.commit()
        return '', 204

@api.route('/total')
class TotalRewards(Resource):
    # @api.doc(security='BearerAuth')  # Commented out for testing
    # @token_required  # Commented out for testing
    def get(self):
        """Get total reward points for the current user"""
        user_id = 1  # Assume user ID 1 for testing
        total_points = db.session.query(db.func.sum(Reward.points)).filter_by(user_id=user_id).scalar() or 0
        return {'user_id': user_id, 'total_points': total_points}, 200