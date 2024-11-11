from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.user_reports import UserReport  # Assuming user reports are in this model
from app.extensions import db
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased  # Import aliased from sqlalchemy.orm
import statistics
from datetime import datetime, timedelta

api = Namespace('trains', description='Train related operations')

# Update station model to include actual times and delays
station_model = api.model('Station', {
    'id': fields.Integer,
    'name_en': fields.String,
    'name_ar': fields.String,
    'code': fields.String,
    'location_lat': fields.Float,
    'location_long': fields.Float,
    'scheduled_arrival_time': fields.String(description='Scheduled arrival time at the station in HH:MM:SS format'),
    'scheduled_departure_time': fields.String(description='Scheduled departure time from the station in HH:MM:SS format'),
    'actual_arrival_time': fields.String(description='Actual arrival time based on user reports'),
    'actual_departure_time': fields.String(description='Actual departure time based on user reports'),
    'delay_time': fields.Integer(description='Delay time in minutes'),
    'number_of_reports': fields.Integer(description='Number of user reports for this station'),
})

# Train model definition
train_model = api.model('Train', {
    'train_number': fields.Integer,
    'train_type': fields.String,
    'departure_station': fields.Nested(station_model),
    'arrival_station': fields.Nested(station_model),
    'list_of_stations': fields.List(fields.Nested(station_model)),
    'number_of_stations': fields.Integer,
    'is_favourite': fields.Boolean,
    'notification_enabled': fields.Boolean,
    'last_reported_station': fields.String(description='Last station reported by users'),
    'last_report_time': fields.String(description='Time of the last report for this train')
})


# Pagination and train list parser with additional 'page' argument for pagination
train_list_parser = reqparse.RequestParser()
train_list_parser.add_argument('departure_station_id', type=int, required=False, help='Filter by departure station ID')
train_list_parser.add_argument('arrival_station_id', type=int, required=False, help='Filter by arrival station ID')
train_list_parser.add_argument('page', type=int, required=False, default=1, help='Page number for pagination')


from datetime import datetime, timedelta
import statistics
from app import db
from app.models.route import Route
from app.models.user_reports import UserReport

def calculate_average_time(report_times):
    """
    Calculates the average time from a list of datetime objects.

    Args:
    report_times (list): A list of datetime objects.

    Returns:
    datetime: The average time as a datetime object, or None if the list is empty.
    """
    if not report_times:
        return None

    # Convert datetime objects to timestamps (seconds since epoch)
    numeric_times = [time.timestamp() for time in report_times]

    if len(numeric_times) > 2:
        # Calculate the mean of the timestamps
        avg_timestamp = statistics.mean(numeric_times)

        # Convert the average timestamp back to a datetime object
        return datetime.fromtimestamp(avg_timestamp)
    else:
        return report_times[0]

def serialize_train(train, favourite_train_numbers, departure_station_id=None, arrival_station_id=None):
    """
    Helper function to serialize train data with actual times, delays, 
    and last reported station information.
    """

    # Get the list of stations for the train
    routes = Route.query.filter_by(train_number=train.train_number).order_by(Route.sequence_number).all()
    list_of_stations = []
    include_station = not departure_station_id  # Start including if departure_station_id is not specified

    last_reported_station = None  # Initialize last_reported_station
    last_report_time = None  # Initialize last_report_time

    for route in routes:
        station = route.station

        # Initialize variables to avoid NameError
        actual_arrival_time = None
        actual_departure_time = None
        delay_time = None

        if not include_station and station.id == departure_station_id:
            include_station = True

        if include_station:
            # Scheduled times
            scheduled_arrival_time = route.scheduled_arrival_time.strftime('%H:%M:%S') if route.scheduled_arrival_time else None
            scheduled_departure_time = route.scheduled_departure_time.strftime('%H:%M:%S') if route.scheduled_departure_time else None

            # Fetch user reports for actual arrival/departure times at this station
            arrival_reports = db.session.query(UserReport.reported_time).filter(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type == 'arrival'
            ).all()
            departure_reports = db.session.query(UserReport.reported_time).filter(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type == 'departure'
            ).all()

            # Process report times (remove outliers, calculate averages)
            arrival_times = [report.reported_time for report in arrival_reports]
            departure_times = [report.reported_time for report in departure_reports]

            # Remove outliers if more than 2 reports
            if len(arrival_times) > 2:
                arrival_times_timestamps = [time.timestamp() for time in arrival_times]
                median_arrival_time = datetime.fromtimestamp(statistics.median(arrival_times_timestamps))
                arrival_times = [time for time in arrival_times if abs((time - median_arrival_time).total_seconds()) < 600]  # 10 min threshold
            if len(departure_times) > 2:
                departure_times_timestamps = [time.timestamp() for time in departure_times]
                median_departure_time = datetime.fromtimestamp(statistics.median(departure_times_timestamps))
                departure_times = [time for time in departure_times if abs((time - median_departure_time).total_seconds()) < 600]

            # Calculate actual arrival/departure
            actual_arrival_time = calculate_average_time(arrival_times)
            actual_departure_time = calculate_average_time(departure_times)

            # Calculate delay in minutes
            if actual_arrival_time and route.scheduled_arrival_time:
                scheduled_datetime = datetime.combine(actual_arrival_time.date(), route.scheduled_arrival_time)
                time_diff_seconds = (actual_arrival_time - scheduled_datetime).total_seconds()
                delay_time = int(round(time_diff_seconds / 60))  # Convert seconds to minutes

            # Update last_reported_station and last_report_time
            if arrival_times or departure_times:
                last_report_time = max(arrival_times + departure_times)
                last_reported_station = station.name_en

            # Prepare station data
            station_data = {
                'id': station.id,
                'name_en': station.name_en,
                'name_ar': station.name_ar,
                'code': station.code,
                'location_lat': float(station.location_lat) if station.location_lat else None,
                'location_long': float(station.location_long) if station.location_long else None,
                'scheduled_arrival_time': scheduled_arrival_time,
                'scheduled_departure_time': scheduled_departure_time,
                'actual_arrival_time': actual_arrival_time.strftime('%H:%M:%S') if actual_arrival_time else None,
                'actual_departure_time': actual_departure_time.strftime('%H:%M:%S') if actual_departure_time else None,
                'delay_time': delay_time,
                'number_of_reports': len(arrival_times) + len(departure_times)
                }
            list_of_stations.append(station_data)

        if arrival_station_id and station.id == arrival_station_id:
            break

    # Compile the train data
    train_data = {
        'train_number': train.train_number,
        'train_type': train.train_type,
        'departure_station': list_of_stations[0] if list_of_stations else None,
        'arrival_station': list_of_stations[-1] if list_of_stations else None,
        'list_of_stations': list_of_stations,
        'number_of_stations': len(list_of_stations),
        'is_favourite': train.train_number in favourite_train_numbers,
        'notification_enabled': False,  # Implement logic if needed
        'last_reported_station': last_reported_station,
        'last_report_time': last_report_time.strftime('%Y-%m-%d %H:%M:%S') if last_report_time else None
    }

    return train_data

@api.route('/')
class TrainList(Resource):
    @api.expect(train_list_parser)
    @api.marshal_list_with(train_model)
    def get(self):
        """List all trains with optional filters and pagination"""
        user_id = 1  # For testing purposes

        # Parse query parameters
        args = train_list_parser.parse_args()
        departure_station_id = args.get('departure_station_id')
        arrival_station_id = args.get('arrival_station_id')
        page = args.get('page', 1)

        # Base query for trains
        query = db.session.query(Train).distinct()

        if departure_station_id or arrival_station_id:
            # Only include trains that pass through the specified departure or arrival station
            query = query.join(Route, Train.train_number == Route.train_number)

            # Filter for trains that include the specified stations in their route
            if departure_station_id and arrival_station_id:
                query = query.filter(
                    db.or_(
                        Route.station_id == departure_station_id,
                        Route.station_id == arrival_station_id
                    )
                )
            elif departure_station_id:
                query = query.filter(Route.station_id == departure_station_id)
            elif arrival_station_id:
                query = query.filter(Route.station_id == arrival_station_id)

        # Pagination: limit results to 10 per page
        page_size = 10
        offset = (page - 1) * page_size
        trains = query.limit(page_size).offset(offset).all()

        # Fetch user's favourite trains
        favourite_train_numbers = [
            fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        ]

        # Serialize train list with all route stations if the train passes through specified stations
        train_list = [
            serialize_train(train, favourite_train_numbers, departure_station_id, arrival_station_id)
            for train in trains
        ]

        return train_list

@api.route('/<int:train_number>')
@api.param('train_number', 'The train number')
class TrainResource(Resource):
    @api.expect(train_list_parser)
    @api.marshal_with(train_model)
    def get(self, train_number):
        """Get a specific train by train number with optional station filters"""
        user_id = 1  # For testing purposes

        # Parse query parameters
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