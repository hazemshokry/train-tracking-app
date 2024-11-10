# app/models/__init__.py

from .train import Train
from .station import Station
from .route import Route
from .user import User
from .user_favourite_trains import UserFavouriteTrain
from .user_reports import UserReport
from .calculated_times import CalculatedTime
from .notifications import Notification
from .rewards import Reward
from .user_notification_settings import UserNotificationSetting

# Optionally, define __all__ to specify what is exported when 'from app.models import *' is used
__all__ = [
    'Train',
    'Station',
    'Route',
    'User',
    'UserFavouriteTrain',
    'UserReport',
    'CalculatedTime',
    'Notification',
    'Reward',
    'UserNotificationSetting',
]