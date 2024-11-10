# app/models/user_notification_settings.py

from app.extensions import db

class UserNotificationSetting(db.Model):
    __tablename__ = 'usernotificationsettings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    notification_enabled = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('notification_setting', uselist=False))

    def __repr__(self):
        return f"<UserNotificationSetting User {self.user_id} Notification Enabled {self.notification_enabled}>"