from flask_restx import Api

api = Api(
    title='Train Tracking API',
    version='1.0',
    description='APIs for tracking trains and stations',
    doc='/docs',  # Swagger UI available at /docs
)

# Import namespaces
from .train_routes import api as train_ns
from .station_routes import api as station_ns
from .user_routes import api as user_ns
from .report_routes import api as report_ns
from .notification_routes import api as notification_ns
from .reward_routes import api as reward_ns

# Add namespaces
api.add_namespace(train_ns, path='/trains')
api.add_namespace(station_ns, path='/stations')
api.add_namespace(user_ns, path='/users')
api.add_namespace(report_ns, path='/reports')
api.add_namespace(notification_ns, path='/notifications')
api.add_namespace(reward_ns, path='/rewards')