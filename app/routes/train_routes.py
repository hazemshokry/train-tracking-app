from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.user_reports import UserReport
from app.extensions import db
from sqlalchemy import func, or_, and_
import statistics
from datetime import datetime, timedelta

api = Namespace('trains', description='Train related operations')

# Station model definition
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

# Train list parser
train_list_parser = reqparse.RequestParser()
train_list_parser.add_argument('departure_station_id', type=int, required=False, help='Filter by departure station ID')
train_list_parser.add_argument('arrival_station_id', type=int, required=False, help='Filter by arrival station ID')
train_list_parser.add_argument('page', type=int, required=False, default=1, help='Page number for pagination')

def calculate_average_time(report_times):
    if not report_times:
        return None
    numeric_times = [time.timestamp() for time in report_times]
    if len(numeric_times) > 2:
        avg_timestamp = statistics.mean(numeric_times)
        return datetime.fromtimestamp(avg_timestamp)
    else:
        return report_times[0]

def serialize_train(train, favourite_train_numbers):
    routes = Route.query.filter_by(train_number=train.train_number).order_by(Route.sequence_number).all()
    list_of_stations = []
    last_reported_station = None
    last_report_time = None
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # Define datetime bounds for today and tomorrow
    start_datetime = datetime.combine(today, datetime.min.time())
    end_datetime = datetime.combine(tomorrow, datetime.max.time())

    for route in routes:
        station = route.station
        actual_arrival_time = actual_departure_time = delay_time = None

        # Keep scheduled times as time-only values
        scheduled_arrival_time = route.scheduled_arrival_time
        scheduled_departure_time = route.scheduled_departure_time

        # Fetch user report times (filtered by today and tomorrow)
        arrival_reports = db.session.query(UserReport.reported_time).filter(
            and_(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type.in_(['arrival', 'offboard']),
                UserReport.reported_time >= start_datetime,
                UserReport.reported_time <= end_datetime
            )
        ).all()
        departure_reports = db.session.query(UserReport.reported_time).filter(
            and_(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type.in_(['departure', 'onboard']),
                UserReport.reported_time >= start_datetime,
                UserReport.reported_time <= end_datetime
            )
        ).all()

        # Convert arrival and departure report times to datetime for today or tomorrow
        arrival_times = [
            datetime.combine(today, report.reported_time.time()) if report.reported_time.date() == today
            else datetime.combine(tomorrow, report.reported_time.time())
            for report in arrival_reports
        ]
        departure_times = [
            datetime.combine(today, report.reported_time.time()) if report.reported_time.date() == today
            else datetime.combine(tomorrow, report.reported_time.time())
            for report in departure_reports
        ]

        actual_arrival_time = calculate_average_time(arrival_times)
        actual_departure_time = calculate_average_time(departure_times)

        # Calculate delay time for arrival or departure
        if actual_arrival_time and scheduled_arrival_time:
            scheduled_datetime = datetime.combine(actual_arrival_time.date(), scheduled_arrival_time)
            time_diff_seconds = (actual_arrival_time - scheduled_datetime).total_seconds()
            delay_time = int(round(time_diff_seconds / 60))
        elif actual_departure_time and scheduled_departure_time:
            scheduled_datetime = datetime.combine(actual_departure_time.date(), scheduled_departure_time)
            time_diff_seconds = (actual_departure_time - scheduled_datetime).total_seconds()
            delay_time = int(round(time_diff_seconds / 60))

        # Update last reported station and last report time based on any report at this station
        if arrival_times or departure_times:
            last_reported_station = station.name_en
            # Set last_report_time to the latest available actual time for the last reported station
            last_report_time = max(
                [actual_arrival_time, actual_departure_time],
                key=lambda x: x if x is not None else datetime.min
            )

        # Append station data
        station_data = {
            'id': station.id,
            'name_en': station.name_en,
            'name_ar': station.name_ar,
            'code': station.code,
            'location_lat': float(station.location_lat) if station.location_lat else None,
            'location_long': float(station.location_long) if station.location_long else None,
            'scheduled_arrival_time': scheduled_arrival_time.strftime('%H:%M:%S') if scheduled_arrival_time else None,
            'scheduled_departure_time': scheduled_departure_time.strftime('%H:%M:%S') if scheduled_departure_time else None,
            'actual_arrival_time': actual_arrival_time.strftime('%Y-%m-%d %H:%M:%S') if actual_arrival_time else None,
            'actual_departure_time': actual_departure_time.strftime('%Y-%m-%d %H:%M:%S') if actual_departure_time else None,
            'delay_time': delay_time,
            'number_of_reports': len(arrival_times) + len(departure_times),
        }
        list_of_stations.append(station_data)

    # Compile train data
    train_data = {
        'train_number': train.train_number,
        'train_type': train.train_type,
        'departure_station': list_of_stations[0] if list_of_stations else None,
        'arrival_station': list_of_stations[-1] if list_of_stations else None,
        'list_of_stations': list_of_stations,
        'number_of_stations': len(list_of_stations),
        'is_favourite': train.train_number in favourite_train_numbers,
        'notification_enabled': False,
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
        args = train_list_parser.parse_args()
        departure_station_id = args.get('departure_station_id')
        arrival_station_id = args.get('arrival_station_id')
        page = args.get('page', 1)

        query = db.session.query(Train).distinct()
        if departure_station_id and arrival_station_id:
            # Trains that have both stations in their routes
            train_numbers_with_departure_station = db.session.query(Route.train_number).filter(
                Route.station_id == departure_station_id
            ).subquery().select()

            train_numbers_with_arrival_station = db.session.query(Route.train_number).filter(
                Route.station_id == arrival_station_id
            ).subquery().select()

            query = query.filter(
                Train.train_number.in_(train_numbers_with_departure_station)
            ).filter(
                Train.train_number.in_(train_numbers_with_arrival_station)
            )
        
        elif departure_station_id:
            train_numbers_with_departure_station = db.session.query(Route.train_number).filter(
                Route.station_id == departure_station_id
            ).subquery().select()

            query = query.filter(Train.train_number.in_(train_numbers_with_departure_station))
        
        elif arrival_station_id:
            train_numbers_with_arrival_station = db.session.query(Route.train_number).filter(
                Route.station_id == arrival_station_id
            ).subquery().select()

            query = query.filter(Train.train_number.in_(train_numbers_with_arrival_station))

        page_size = 10
        offset = (page - 1) * page_size
        trains = query.limit(page_size).offset(offset).all()

        favourite_train_numbers = [fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()]
        train_list = [serialize_train(train, favourite_train_numbers) for train in trains]

        return train_list

@api.route('/<int:train_number>')
@api.param('train_number', 'The train number')
class TrainResource(Resource):
    @api.expect(train_list_parser)
    @api.marshal_with(train_model)
    def get(self, train_number):
        """Get a specific train by train number"""
        user_id = 1  # For testing purposes
        train = Train.query.filter_by(train_number=train_number).first()
        if not train:
            api.abort(404, f"Train {train_number} not found")

        favourite_train_numbers = [fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()]
        train_data = serialize_train(train, favourite_train_numbers)

        return train_data
