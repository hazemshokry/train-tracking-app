from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.user_reports import UserReport
from app.models.operations import Operation
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
    # Determine today's date and set up previous and next days
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # Fetch or create Operation for today
    operation_today = Operation.query.filter_by(train_number=train.train_number, operational_date=today).first()
    if not operation_today:
        operation_today = Operation(
            train_number=train.train_number,
            operational_date=today,
            status="on time"
        )
        db.session.add(operation_today)
        db.session.flush()

    # Fetch Operation for yesterday and tomorrow for cross-day handling
    operation_yesterday = Operation.query.filter_by(train_number=train.train_number, operational_date=yesterday).first()
    operation_tomorrow = Operation.query.filter_by(train_number=train.train_number, operational_date=tomorrow).first()

    # Retrieve the train routes and prepare to iterate stations
    routes = Route.query.filter_by(train_number=train.train_number).order_by(Route.sequence_number).all()
    list_of_stations = []
    last_reported_station = None
    last_report_time = None

    for route in routes:
        station = route.station
        actual_arrival_time = actual_departure_time = delay_time = None

        # Get scheduled arrival and departure times
        scheduled_arrival_time = route.scheduled_arrival_time
        scheduled_departure_time = route.scheduled_departure_time

        # Retrieve user reports based on operation date
        arrival_reports_today = db.session.query(UserReport.reported_time).filter(
            UserReport.train_number == train.train_number,
            UserReport.station_id == station.id,
            UserReport.report_type.in_(['arrival', 'offboard']),
            UserReport.operation_id == operation_today.id
        ).all()

        # For trains that arrive past midnight, we include reports for both yesterday's and today's operations
        if scheduled_arrival_time and scheduled_arrival_time.hour < 6:  # Adjust this as needed for your "next day" range
            arrival_reports_yesterday = db.session.query(UserReport.reported_time).filter(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type.in_(['arrival', 'offboard']),
                UserReport.operation_id == operation_yesterday.id
            ).all()
            arrival_reports_today += arrival_reports_yesterday

        # Retrieve departure reports in a similar manner
        departure_reports_today = db.session.query(UserReport.reported_time).filter(
            UserReport.train_number == train.train_number,
            UserReport.station_id == station.id,
            UserReport.report_type.in_(['departure', 'onboard']),
            UserReport.operation_id == operation_today.id
        ).all()

        # Include reports for both today's and tomorrow's operations for post-midnight departures
        if scheduled_departure_time and scheduled_departure_time.hour < 6:  # Adjust as needed
            departure_reports_tomorrow = db.session.query(UserReport.reported_time).filter(
                UserReport.train_number == train.train_number,
                UserReport.station_id == station.id,
                UserReport.report_type.in_(['departure', 'onboard']),
                UserReport.operation_id == operation_tomorrow.id
            ).all()
            departure_reports_today += departure_reports_tomorrow

        # Combine and average the arrival and departure report times
        arrival_times = [report.reported_time for report in arrival_reports_today]
        departure_times = [report.reported_time for report in departure_reports_today]

        actual_arrival_time = calculate_average_time(arrival_times)
        actual_departure_time = calculate_average_time(departure_times)

        # Calculate delay time
        if actual_arrival_time and scheduled_arrival_time:
            scheduled_datetime = datetime.combine(actual_arrival_time.date(), scheduled_arrival_time)
            time_diff_seconds = (actual_arrival_time - scheduled_datetime).total_seconds()
            delay_time = int(round(time_diff_seconds / 60))
        elif actual_departure_time and scheduled_departure_time:
            scheduled_datetime = datetime.combine(actual_departure_time.date(), scheduled_departure_time)
            time_diff_seconds = (actual_departure_time - scheduled_datetime).total_seconds()
            delay_time = int(round(time_diff_seconds / 60))

        # Update last reported station based on any report at this station
        if arrival_times or departure_times:
            last_reported_station = station.name_en
            last_report_time = max([actual_arrival_time, actual_departure_time], key=lambda x: x if x else datetime.min)

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
