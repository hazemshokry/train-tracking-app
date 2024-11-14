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
    'scheduled_time': fields.String(description='Scheduled time at the station in HH:MM:SS format'),
    'actual_time': fields.String(description='Actual time based on user reports'),
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
    'last_report_time': fields.String(description='Time of the last report for this train'),
    'previous_station': fields.String(description='Previous station reported by users'),
    'next_station': fields.String(description='Next station reported by users'),
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

    # Retrieve the train routes and prepare to iterate stations
    routes = Route.query.filter_by(train_number=train.train_number).order_by(Route.sequence_number).all()
    list_of_stations = []
    last_reported_station = None
    last_report_time = None
    prev_station_ar = None
    prev_station_actual_time = None
    next_station_ar = None

    for i, route in enumerate(routes):
        station = route.station
        actual_time = delay_time = None

        # Select either scheduled arrival or departure time, based on availability
        scheduled_time = route.scheduled_arrival_time or route.scheduled_departure_time

        # Retrieve user reports for actual time, combining both arrival and departure types
        report_times = db.session.query(UserReport.reported_time).filter(
            UserReport.train_number == train.train_number,
            UserReport.station_id == station.id,
            UserReport.operation_id == operation_today.id,
            UserReport.report_type.in_(['arrival', 'offboard', 'departure', 'onboard'])
        ).all()

        # Average the report times if available
        report_times = [report.reported_time for report in report_times]
        actual_time = calculate_average_time(report_times)

        # Calculate delay time if both scheduled and actual times are available
        if actual_time and scheduled_time:
            scheduled_datetime = datetime.combine(actual_time.date(), scheduled_time)
            time_diff_seconds = (actual_time - scheduled_datetime).total_seconds()
            delay_time = int(round(time_diff_seconds / 60))

        # Update last reported station and neighboring stations
        if report_times:
            last_reported_station = station.name_ar
            last_report_time = actual_time
            if i > 0:
                prev_station_ar = routes[i - 1].station.name_ar
                prev_station_actual_time = calculate_average_time(
                    [report.reported_time for report in db.session.query(UserReport.reported_time).filter(
                        UserReport.train_number == train.train_number,
                        UserReport.station_id == routes[i - 1].station.id,
                        UserReport.operation_id == operation_today.id,
                        UserReport.report_type.in_(['arrival', 'offboard', 'departure', 'onboard'])
                    ).all()]
                )
            if i < len(routes) - 1:
                next_station_ar = routes[i + 1].station.name_ar

        # Append station data with only one scheduled and one actual time
        station_data = {
            'id': station.id,
            'name_en': station.name_en,
            'name_ar': station.name_ar,
            'code': station.code,
            'location_lat': float(station.location_lat) if station.location_lat else None,
            'location_long': float(station.location_long) if station.location_long else None,
            'scheduled_time': scheduled_time.strftime('%H:%M:%S') if scheduled_time else None,
            'actual_time': actual_time.strftime('%Y-%m-%d %H:%M:%S') if actual_time else None,
            'delay_time': delay_time,
            'number_of_reports': len(report_times),
        }
        list_of_stations.append(station_data)

    # Construct train data with neighboring station names in Arabic and actual time for previous station
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
        'last_report_time': last_report_time.strftime('%Y-%m-%d %H:%M:%S') if last_report_time else None,
        'previous_station': {
            'name_ar': prev_station_ar,
            'actual_time': prev_station_actual_time.strftime('%Y-%m-%d %H:%M:%S') if prev_station_actual_time else None
        } if prev_station_ar else None,
        'next_station': next_station_ar
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
            # Get trains that have both stations in sequence
            subquery_departure = db.session.query(Route.train_number, Route.sequence_number).filter(
                Route.station_id == departure_station_id
            ).subquery()

            subquery_arrival = db.session.query(Route.train_number, Route.sequence_number).filter(
                Route.station_id == arrival_station_id
            ).subquery()

            query = query.join(subquery_departure, Train.train_number == subquery_departure.c.train_number)
            query = query.join(subquery_arrival, Train.train_number == subquery_arrival.c.train_number)

            # Apply sequence constraint: arrival must come after departure in the route
            query = query.filter(subquery_departure.c.sequence_number < subquery_arrival.c.sequence_number)
        
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

        # Pagination
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
