# app/routes/notification_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import Notification, User, Train, DeviceToken, TrainSubscription # Import TrainSubscription
from app.extensions import db
from datetime import datetime
from app.utils.auth_utils import token_required


api = Namespace('notifications', description='Notification related operations')

# Serializer models
notification_model = api.model('Notification', {
    'id': fields.Integer(readOnly=True, description='Unique identifier of the notification'),
    'user_id': fields.String(description='ID of the user'),
    'train_number': fields.String(description='Train number'),
    'title': fields.String(description='Title of the notification'),
    'description': fields.String(description='Description of the notification'),
    'time': fields.DateTime(description='Time the notification was created'),
    'is_read': fields.Boolean(description='Read status of the notification'),
})

notification_create_model = api.model('NotificationCreate', {
    'train_number': fields.String(description='Train number'),
    'title': fields.String(required=True, description='Title of the notification'),
    'description': fields.String(description='Description of the notification'),
})

@api.route('/')
class NotificationList(Resource):
    @token_required
    @api.marshal_list_with(notification_model)
    def get(self):
        """List all notifications for the current user"""
        user_id = request.current_user.id
        notifications = Notification.query.filter_by(user_id=user_id).all()
        return notifications

    @token_required
    @api.expect(notification_create_model)
    @api.marshal_with(notification_model, code=201)
    def post(self):
        """Create a new notification for all users subscribed to a train"""
        data = api.payload
        train_number = data.get('train_number')
        title = data['title']
        description = data.get('description')

        if not train_number:
            api.abort(400, 'Train number is required to send notifications')

        train = Train.query.get(train_number)
        if not train:
            api.abort(404, 'Train not found')

        subscriptions = TrainSubscription.query.filter_by(train_number=train_number).all()
        
        if not subscriptions:
            return {'message': 'No users subscribed to this train'}, 200

        for sub in subscriptions:
            # Create a notification for each subscribed user
            new_notification = Notification(
                user_id=sub.user_id,
                train_number=train_number,
                title=title,
                description=description,
            )
            db.session.add(new_notification)
            
            # Fetch the latest device token for the user
            device_token = DeviceToken.query.filter_by(user_id=sub.user_id).order_by(DeviceToken.created_at.desc()).first()
            if device_token:
                # Here you would integrate with your FCM service
                print(f"Sending FCM notification to {device_token.token} for user {sub.user_id}")
                
        db.session.commit()
        
        return {'message': f'Notifications sent to {len(subscriptions)} users'}, 201

@api.route('/read-all')
class NotificationReadAll(Resource):
    @token_required
    @api.response(200, 'All notifications marked as read')
    def put(self):
        """Mark all notifications as read for the current user"""
        user_id = request.current_user.id
        
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()

        if not notifications:
            return {'message': 'No unread notifications to mark as read'}, 200

        for notification in notifications:
            notification.is_read = True
        
        db.session.commit()

        return {'message': 'All notifications marked as read'}, 200

@api.route('/<int:id>')
@api.param('id', 'The notification identifier')
class NotificationResource(Resource):
    @token_required
    @api.marshal_with(notification_model)
    def get(self, id):
        """Get a notification by ID"""
        notification = Notification.query.get_or_404(id)
        if request.current_user.id != notification.user_id:
            api.abort(403, 'Access forbidden')
        return notification

    @token_required
    @api.response(204, 'Notification marked as read')
    def put(self, id):
        """Mark a notification as read"""
        notification = Notification.query.get_or_404(id)
        if request.current_user.id != notification.user_id:
            api.abort(403, 'Access forbidden')

        notification.is_read = True
        db.session.commit()
        return '', 204

    @token_required
    @api.response(204, 'Notification deleted')
    def delete(self, id):
        """Delete a notification by ID"""
        notification = Notification.query.get_or_404(id)
        if request.current_user.id != notification.user_id:
            api.abort(403, 'Access forbidden')

        db.session.delete(notification)
        db.session.commit()
        return '', 204