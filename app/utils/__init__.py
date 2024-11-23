from flask_restx import Api

api = Api(
    title='Train Tracking API',
    version='1.0',
    description='APIs for tracking trains and stations',
    doc='/docs',  # Swagger UI available at /docs
)