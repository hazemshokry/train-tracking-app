# app/routes/train_routes.py

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.user_favourite_trains import UserFavouriteTrain
from app.extensions import db

api = Namespace('trains', description='Train related operations')

# Serializer models
station_model = api.model('Station', {
    'id': fields.Integer,
    'name_en': fields.String,
    'name_ar': fields.String,
    'code': fields.String,
    'location_lat': fields.Float,
    'location_long': fields.Float,
    'scheduled_arrival_time': fields.String(description='Arrival time at the station in HH:MM:SS format'),
    'scheduled_departure_time': fields.String(description='Departure time from the station in HH:MM:SS format'),
})

train_model = api.model('Train', {
    'train_number': fields.Integer,
    'train_type': fields.String,
    'departure_station': fields.Nested(station_model),
    'arrival_station': fields.Nested(station_model),
    'number_of_votes': fields.Integer,
    'delay_time': fields.Integer,
    'list_of_stations': fields.List(fields.Nested(station_model)),
    'number_of_stations': fields.Integer,
    'is_favourite': fields.Boolean,
    'notification_enabled': fields.Boolean,
})

# Request parser without scheduled times
train_list_parser = reqparse.RequestParser()
train_list_parser.add_argument('departure_station_id', type=int, required=False, help='Filter by departure station ID')
train_list_parser.add_argument('arrival_station_id', type=int, required=False, help='Filter by arrival station ID')

@api.route('/')
class TrainList(Resource):
    @api.expect(train_list_parser)
    @api.marshal_list_with(train_model)
    def get(self):
        """List all trains with optional filters"""
        user_id = 1  # For testing purposes

        # Parse the query parameters
        args = train_list_parser.parse_args()
        departure_station_id = args.get('departure_station_id')
        arrival_station_id = args.get('arrival_station_id')

        # Build the base query
        query = db.session.query(Train).distinct()

        if departure_station_id and arrival_station_id:
            # Both departure and arrival station IDs are provided
            RouteDeparture = aliased(Route)
            RouteArrival = aliased(Route)

            query = query.join(RouteDeparture, Train.train_number == RouteDeparture.train_number)\
                         .join(RouteArrival, Train.train_number == RouteArrival.train_number)\
                         .filter(
                             RouteDeparture.station_id == departure_station_id,
                             RouteArrival.station_id == arrival_station_id,
                             RouteDeparture.sequence_number < RouteArrival.sequence_number
                         )
        elif departure_station_id:
            # Only departure_station_id is provided
            query = query.join(Route, Train.train_number == Route.train_number)\
                         .filter(Route.station_id == departure_station_id)
        elif arrival_station_id:
            # Only arrival_station_id is provided
            query = query.join(Route, Train.train_number == Route.train_number)\
                         .filter(Route.station_id == arrival_station_id)
        else:
            # No filters, get all trains
            pass

        # Fetch trains from the database
        trains = query.all()

        # Fetch user's favourite trains
        favourite_train_numbers = [
            fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        ]

        train_list = []
        for train in trains:
            train_data = serialize_train(train, favourite_train_numbers, departure_station_id, arrival_station_id)
            train_list.append(train_data)

        return train_list

@api.route('/<int:train_number>')
@api.param('train_number', 'The train number')
class TrainResource(Resource):
    @api.expect(train_list_parser)
    @api.marshal_with(train_model)
    def get(self, train_number):
        """Get a specific train by train number with optional station filters"""
        user_id = 1  # For testing purposes

        # Parse the query parameters
        args = train_list_parser.parse_args()
        departure_station_id = args.get('departure_station_id')
        arrival_station_id = args.get('arrival_station_id')

        # Fetch the train from the database
        train = Train.query.filter_by(train_number=train_number).first()
        if not train:
            api.abort(404, f"Train {train_number} not found")

        # Fetch user's favourite trains
        favourite_train_numbers = [
            fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        ]

        # Serialize the train data with station filters
        train_data = serialize_train(train, favourite_train_numbers, departure_station_id, arrival_station_id)

        return train_data

@api.route('/favourites')
class FavouriteTrains(Resource):
    @api.marshal_list_with(train_model)
    def get(self):
        """List all trains favorited by the user"""
        user_id = 1  # Assume user ID is known

        # Retrieve favorite train numbers for the user
        favourite_train_numbers = [
            fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        ]

        # Fetch train details for the favorite train numbers
        favourite_trains = Train.query.filter(Train.train_number.in_(favourite_train_numbers)).all()

        # Serialize the trains
        train_list = [serialize_train(train, favourite_train_numbers) for train in favourite_trains]

        return train_list

@api.route('/favourites/delete_all')
class DeleteAllFavourites(Resource):
    def delete(self):
        """Delete all favorite trains for the user"""
        user_id = 1  # Assume user ID is known

        # Delete all favorite trains for the user
        UserFavouriteTrain.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        return {'message': 'All favorite trains deleted successfully'}, 200

def serialize_train(train, favourite_train_numbers, departure_station_id=None, arrival_station_id=None):
    """Helper function to serialize train data"""
    from datetime import datetime

    # Serialize datetime fields as strings
    scheduled_departure_timestamp_str = train.scheduled_departure_datetime.strftime('%Y-%m-%d %H:%M:%S') if hasattr(train, 'scheduled_departure_datetime') and train.scheduled_departure_datetime else None
    scheduled_arrival_timestamp_str = train.scheduled_arrival_datetime.strftime('%Y-%m-%d %H:%M:%S') if hasattr(train, 'scheduled_arrival_datetime') and train.scheduled_arrival_datetime else None

    # Get the list of stations for the train
    routes = Route.query.filter_by(train_number=train.train_number).order_by(Route.sequence_number).all()

    list_of_stations = []
    include_station = not departure_station_id  # Start including if departure_station_id is not specified
    for route in routes:
        station = route.station

        if not include_station and station.id == departure_station_id:
            include_station = True  # Start including stations from departure_station_id

        if include_station:
            # Build station_data
            arrival_time_str = route.scheduled_arrival_time.strftime('%H:%M:%S') if route.scheduled_arrival_time else None
            departure_time_str = route.scheduled_departure_time.strftime('%H:%M:%S') if route.scheduled_departure_time else None

            station_data = {
                'id': station.id,
                'name_en': station.name_en,
                'name_ar': station.name_ar,
                'code': station.code,
                'location_lat': float(station.location_lat) if station.location_lat else None,
                'location_long': float(station.location_long) if station.location_long else None,
                'scheduled_arrival_time': arrival_time_str,
                'scheduled_departure_time': departure_time_str,
            }
            list_of_stations.append(station_data)

        if arrival_station_id and station.id == arrival_station_id:
            # Include arrival station and stop
            break

    train_data = {
        'train_id': train.id if hasattr(train, 'id') else None,
        'train_number': train.train_number,
        'train_type': train.train_type,
        'departure_station': {
            'id': train.departure_station.id,
            'name_en': train.departure_station.name_en,
            'name_ar': train.departure_station.name_ar,
            'code': train.departure_station.code,
            'location_lat': float(train.departure_station.location_lat) if train.departure_station.location_lat else None,
            'location_long': float(train.departure_station.location_long) if train.departure_station.location_long else None,
            'scheduled_arrival_time': None,
            'scheduled_departure_time': None,
        },
        'scheduled_departure_timestamp': scheduled_departure_timestamp_str,
        'arrival_station': {
            'id': train.arrival_station.id,
            'name_en': train.arrival_station.name_en,
            'name_ar': train.arrival_station.name_ar,
            'code': train.arrival_station.code,
            'location_lat': float(train.arrival_station.location_lat) if train.arrival_station.location_lat else None,
            'location_long': float(train.arrival_station.location_long) if train.arrival_station.location_long else None,
            'scheduled_arrival_time': None,
            'scheduled_departure_time': None,
        },
        'scheduled_arrival_timestamp': scheduled_arrival_timestamp_str,
        'number_of_votes': None,  # Set to None as per your request
        'delay_time': None,       # Set to None as per your request
        'list_of_stations': list_of_stations,
        'number_of_stations': len(list_of_stations),
        'is_favourite': train.train_number in favourite_train_numbers,
        'notification_enabled': False,  # Implement logic if needed
    }

    return train_data