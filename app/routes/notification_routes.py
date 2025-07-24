# app/routes/notification_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields
from app.models import Notification, User, Train, DeviceToken # Import DeviceToken
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
    # @token_required
    @api.marshal_list_with(notification_model)
    def get(self):
        """List all notifications for the current user"""
        user_id = "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e"  # Hardcoded for testing
        notifications = Notification.query.filter_by(user_id=user_id).all()
        return notifications

    # @token_required
    @api.expect(notification_create_model)
    @api.marshal_with(notification_model, code=201)
    def post(self):
        """Create a new notification for the current user"""
        data = api.payload
        user_id = "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e"  # Hardcoded for testing
        train_number = data.get('train_number')
        title = data['title']
        description = data.get('description')

        # If train_number is provided, validate it
        if train_number:
            train = Train.query.get(train_number)
            if not train:
                api.abort(400, 'Train not found')

        new_notification = Notification(
            user_id=user_id,
            train_number=train_number,
            title=title,
            description=description,
        )
        db.session.add(new_notification)
        db.session.commit()
        
        # --- Updated Firebase Logic ---
        # Fetch all device tokens for the user
        device_tokens = DeviceToken.query.filter_by(user_id=user_id).all()
        if device_tokens:
            # Loop through each token and send a notification
            for dt in device_tokens:
                # e.g., send_firebase_notification(dt.token, title, description)
                print(f"Would send Firebase notification to token: {dt.token}")
        
        return new_notification, 201

@api.route('/read-all')
class NotificationReadAll(Resource):
    # @token_required
    @api.response(200, 'All notifications marked as read')
    def put(self):
        """Mark all notifications as read for the current user"""
        user_id = "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e"  # Hardcoded for testing
        
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
    # @token_required
    @api.marshal_with(notification_model)
    def get(self, id):
        """Get a notification by ID"""
        notification = Notification.query.get_or_404(id)
        # Ensure the user is accessing their own notification
        if "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e" != notification.user_id: # Hardcoded for testing
            api.abort(403, 'Access forbidden')
        return notification

    # @token_required
    @api.response(204, 'Notification marked as read')
    def put(self, id):
        """Mark a notification as read"""
        notification = Notification.query.get_or_404(id)
        # Ensure the user is updating their own notification
        if "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e" != notification.user_id: # Hardcoded for testing
            api.abort(403, 'Access forbidden')

        notification.is_read = True
        db.session.commit()
        return '', 204

    # @token_required
    @api.response(204, 'Notification deleted')
    def delete(self, id):
        """Delete a notification by ID"""
        notification = Notification.query.get_or_404(id)
        # Ensure the user is deleting their own notification
        if "a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e" != notification.user_id: # Hardcoded for testing
            api.abort(403, 'Access forbidden')

        db.session.delete(notification)
        db.session.commit()
        return '', 204