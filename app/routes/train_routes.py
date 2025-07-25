from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from app.models.train import Train
from app.models.station import Station
from app.models.route import Route
from app.models.user_favourite_trains import UserFavouriteTrain
from app.models.user_reports import UserReport
from app.models.operations import Operation
from app.models.train_subscription import TrainSubscription
from app.extensions import db
from sqlalchemy import func, or_, and_
import statistics
from datetime import datetime, timedelta, timezone
from flask_restx import inputs
from app.utils.auth_utils import token_required

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
    'train_number': fields.String,
    'train_type': fields.String,
    'departure_station': fields.Nested(station_model),
    'arrival_station': fields.Nested(station_model),
    'list_of_stations': fields.List(fields.Nested(station_model)),
    'number_of_stations': fields.Integer,
    'is_favourite': fields.Boolean,
    'is_subscribed': fields.Boolean, # Added is_subscribed
    'notification_enabled': fields.Boolean,
    'last_reported_station': fields.Nested(api.model('LastReportedStation', {
        'name_ar': fields.String,
        'name_en': fields.String,
        'actual_time': fields.String,
        'number_of_reports': fields.Integer
    })),
    'previous_station': fields.Nested(api.model('PreviousStation', {
        'name_ar': fields.String,
        'name_en': fields.String,
        'actual_time': fields.String,
        'number_of_reports': fields.Integer
    }), allow_null=True),
    'next_station': fields.String(description='Next station name in Arabic'),
})

train_summary_model = api.model('TrainSummary', {
    'train_number': fields.String,
    'train_type'  : fields.String,
    'departure_station': fields.Nested(station_model),
    'arrival_station'  : fields.Nested(station_model),
    'number_of_stations': fields.Integer,
    'is_favourite' : fields.Boolean,
    'is_subscribed': fields.Boolean, # Added is_subscribed
    'notification_enabled': fields.Boolean,
    'last_reported_station': fields.Nested(api.model('LastReportedStationSummary', { # Renamed to avoid conflict
        'name_ar': fields.String,
        'name_en': fields.String,
        'actual_time': fields.String,
        'number_of_reports': fields.Integer
    })),
    'previous_station': fields.Nested(api.model('PreviousStationSummary', { # Renamed to avoid conflict
        'name_ar': fields.String,
        'name_en': fields.String,
        'actual_time': fields.String,
        'number_of_reports': fields.Integer
    }), allow_null=True),
    'next_station': fields.String,
})

# --- Pagination Models (New) ---
paginated_response_model = api.model('PaginatedTrainList', {
    'trains': fields.List(fields.Nested(train_summary_model), description="List of trains for the current page. The detail level depends on the 'include_stations' parameter."),
    'current_page': fields.Integer(description='The current page number.'),
    'total_pages': fields.Integer(description='The total number of pages.'),
    'per_page': fields.Integer(description='The number of items per page.'),
    'has_next': fields.Boolean(description='True if a next page exists.'),
    'total_items': fields.Integer(description='The total number of trains matching the query.')
})

# --- Train list parser (Adjusted) ---
train_list_parser = reqparse.RequestParser()
train_list_parser.add_argument('departure_station_id', type=int, required=False, help='Filter by departure station ID')
train_list_parser.add_argument('arrival_station_id', type=int, required=False, help='Filter by arrival station ID')
train_list_parser.add_argument('page', type=int, required=False, default=1, help='Page number for pagination')
train_list_parser.add_argument('per_page', type=int, required=False, default=10, help='Items per page for pagination')
train_list_parser.add_argument('include_stations',type=inputs.boolean,required=False,default=False,help='If true, embed full list_of_stations for each train.'
)

def calculate_average_time(report_times):
    # This function seems unused, the logic is duplicated inside serialize_train.
    # Keeping it to adhere to the "don't change other logic" instruction.
    if not report_times:
        return None
    numeric_times = [time.timestamp() for time in report_times]
    if len(numeric_times) > 2:
        avg_timestamp = statistics.mean(numeric_times)
        return datetime.fromtimestamp(avg_timestamp)
    else:
        return report_times[0]

def serialize_train(train, favourite_train_numbers, subscribed_train_numbers, *, include_stations: bool = True):
    """
    Build a JSON-serialisable dict for a Train.

    Parameters
    ----------
    train : app.models.train.Train
        ORM object for the train.
    favourite_train_numbers : list[int]
        List of train numbers the current user has marked as favourite.
    subscribed_train_numbers : list[int]
        List of train numbers the current user is subscribed to.
    include_stations : bool, default=True
        If False the returned dict omits the heavyweight `list_of_stations`
        array (used by the list endpoint to keep payloads light).
    """
    # ── resolve operation (today) ───────────────────────────────────────────────
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    # Fetch operations for today and yesterday to handle overnight trains
    operations = Operation.query.filter(
        Operation.train_number == train.train_number,
        Operation.operational_date.in_([today, yesterday])
    ).all()
    
    operation_ids = [op.id for op in operations]

    # If no recent operations found, create one for today
    if not operations:
        operation_today = Operation(
            train_number=train.train_number,
            operational_date=today,
            status="on time",
        )
        db.session.add(operation_today)
        db.session.flush()
        operation_ids.append(operation_today.id)


    # ── fetch ordered route records in a single query ──────────────────────────
    routes = (
        Route.query.filter_by(train_number=train.train_number)
        .order_by(Route.sequence_number)
        .all()
    )
    if not routes:
        # Train has no route records – return a very bare skeleton
        return {
            "train_number": train.train_number,
            "train_type": train.train_type,
            "departure_station": None,
            "arrival_station": None,
            "number_of_stations": 0,
            "is_favourite": train.train_number in favourite_train_numbers,
            "is_subscribed": train.train_number in subscribed_train_numbers,
            "notification_enabled": False,
            "last_reported_station": None,
            "previous_station": None,
            "next_station": None,
            **({"list_of_stations": []} if include_stations else {}),
        }

    # ── helpers ────────────────────────────────────────────────────────────────
    def _station_payload(station, scheduled_time, *, actual_time=None, delay=None, n_reports=0):
        """Return the minimal JSON structure for a station."""
        return {
            "id": station.id,
            "name_en": station.name_en,
            "name_ar": station.name_ar,
            "code": station.code,
            "location_lat": float(station.location_lat) if station.location_lat else None,
            "location_long": float(station.location_long) if station.location_long else None,
            "scheduled_time": scheduled_time.strftime("%H:%M:%S") if scheduled_time else None,
            "actual_time": actual_time.strftime("%Y-%m-%d %H:%M:%S") if actual_time else None,
            "delay_time": delay,
            "number_of_reports": n_reports,
        }

    def _average_time(report_times):
        if not report_times:
            return None
        numeric = [t.timestamp() for t in report_times]
        if len(numeric) > 2:
            return datetime.fromtimestamp(statistics.mean(numeric))
        return report_times[0]

    # ── main loop – iterate once through all stations ──────────────────────────
    list_of_stations = []
    last_reported_station = prev_station = None
    next_station_ar = None

    for idx, route in enumerate(routes):
        st = route.station
        scheduled_t = route.scheduled_arrival_time or route.scheduled_departure_time

        # user-reported times for this station/operation
        report_q = db.session.query(UserReport.reported_time).filter(
            UserReport.train_number == train.train_number,
            UserReport.station_id == st.id,
            UserReport.operation_id.in_(operation_ids),
            UserReport.report_type.in_(["arrival", "offboard", "departure", "onboard"]),
        )
        reports = [r.reported_time for r in report_q]
        actual_t = _average_time(reports)

        delay_min = None
        if actual_t and scheduled_t:
            delta_sec = (actual_t - datetime.combine(actual_t.date(), scheduled_t)).total_seconds()
            delay_min = int(round(delta_sec / 60))

        # Track last / prev / next stations where reports exist
        if reports:
            last_reported_station = {
                "name_ar": st.name_ar,
                "name_en": st.name_en,
                "actual_time": actual_t.strftime("%Y-%m-%d %H:%M:%S") if actual_t else None,
                "number_of_reports": len(reports),
            }
            if idx > 0:
                prev_st = routes[idx - 1].station
                prev_reports = db.session.query(UserReport.reported_time).filter(
                    UserReport.train_number == train.train_number,
                    UserReport.station_id == prev_st.id,
                    UserReport.operation_id.in_(operation_ids),
                    UserReport.report_type.in_(["arrival", "offboard", "departure", "onboard"]),
                )
                prev_times = [r.reported_time for r in prev_reports]
                prev_station = {
                    "name_ar": prev_st.name_ar,
                    "name_en": prev_st.name_en,
                    "actual_time": (_average_time(prev_times).strftime("%Y-%m-%d %H:%M:%S") if prev_times else None),
                    "number_of_reports": len(prev_times),
                }
            if idx < len(routes) - 1:
                next_station_ar = routes[idx + 1].station.name_ar

        # assemble per-station payload (only if caller wants it)
        if include_stations:
            list_of_stations.append(
                _station_payload(
                    st,
                    scheduled_t,
                    actual_time=actual_t,
                    delay=delay_min,
                    n_reports=len(reports),
                )
            )

    # ── departure / arrival station data (always included) ─────────────────────
    first_route, last_route = routes[0], routes[-1]
    departure_station = _station_payload(
        first_route.station,
        first_route.scheduled_arrival_time or first_route.scheduled_departure_time,
    )
    arrival_station = _station_payload(
        last_route.station,
        last_route.scheduled_arrival_time or last_route.scheduled_departure_time,
    )

    # ── final object ───────────────────────────────────────────────────────────
    train_dict = {
        "train_number": train.train_number,
        "train_type": train.train_type,
        "departure_station": departure_station,
        "arrival_station": arrival_station,
        "number_of_stations": len(routes),
        "is_favourite": train.train_number in favourite_train_numbers,
        "is_subscribed": train.train_number in subscribed_train_numbers,
        "notification_enabled": False,
        "last_reported_station": last_reported_station,
        "previous_station": prev_station,
        "next_station": next_station_ar,
    }

    if include_stations:
        train_dict["list_of_stations"] = list_of_stations

    return train_dict
@api.route('/')
class TrainList(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.expect(train_list_parser)
    @api.marshal_with(paginated_response_model)
    def get(self):
        """
        List all trains with optional filters and pagination.

        Query-string parameters
        -----------------------
        departure_station_id : int   filter trains that depart from this station
        arrival_station_id   : int   filter trains that arrive at this station
        page                 : int   page number (default 1)
        per_page             : int   items per page (default 10)
        include_stations     : bool  if *true* include the heavy `list_of_stations`
                                     array; otherwise return the compact summary
        """
        user_id = request.current_user.id
        args = train_list_parser.parse_args()
        departure_station_id = args.get('departure_station_id')
        arrival_station_id   = args.get('arrival_station_id')
        page                 = args.get('page')
        per_page             = args.get('per_page')
        include_stations     = args.get('include_stations', False)

        # ── build the base query ───────────────────────────────────────────────
        query = db.session.query(Train)

        if departure_station_id and arrival_station_id:
            dep_sq = db.session.query(Route.train_number, Route.sequence_number).filter(Route.station_id == departure_station_id).subquery()
            arr_sq = db.session.query(Route.train_number, Route.sequence_number).filter(Route.station_id == arrival_station_id).subquery()
            query = (
                query
                .join(dep_sq, Train.train_number == dep_sq.c.train_number)
                .join(arr_sq, Train.train_number == arr_sq.c.train_number)
                .filter(dep_sq.c.sequence_number < arr_sq.c.sequence_number)
            )
        elif departure_station_id:
            train_nums = db.session.query(Route.train_number).filter(Route.station_id == departure_station_id).subquery().select()
            query = query.filter(Train.train_number.in_(train_nums))
        elif arrival_station_id:
            train_nums = db.session.query(Route.train_number).filter(Route.station_id == arrival_station_id).subquery().select()
            query = query.filter(Train.train_number.in_(train_nums))

        # --- Order trains by scheduled departure time ---
        departure_route = db.aliased(Route)
        query = query.join(
            departure_route,
            Train.train_number == departure_route.train_number
        )
        query = query.filter(departure_route.sequence_number == 1)
        query = query.order_by(departure_route.scheduled_departure_time)

        # --- Pagination (Adjusted) ---
        paginated_trains = query.paginate(page=page, per_page=per_page, error_out=False)
        trains = paginated_trains.items

        # ── favourites and subscriptions for the current user ────────────────────────────────────
        favourite_train_numbers = [
            fav.train_number
            for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()
        ]
        subscribed_train_numbers = [
            sub.train_number
            for sub in TrainSubscription.query.filter_by(user_id=user_id).all()
        ]


        # ── serialise ──────────────────────────────────────────────────────────
        train_list = [
            serialize_train(
                train,
                favourite_train_numbers,
                subscribed_train_numbers,
                include_stations=include_stations,
            )
            for train in trains
        ]

        # --- Choose the right schema for marshalling the inner list ---
        schema = train_model if include_stations else train_summary_model
        
        # --- Construct final response object ---
        return {
            'trains': api.marshal(train_list, schema),
            'current_page': paginated_trains.page,
            'total_pages': paginated_trains.pages,
            'per_page': paginated_trains.per_page,
            'has_next': paginated_trains.has_next,
            'total_items': paginated_trains.total
        }


@api.route('/<string:train_number>')
@api.param('train_number', 'The train number')
class TrainResource(Resource):
    @token_required
    @api.doc(security='BearerAuth')
    @api.marshal_with(train_model) # No change here, returns a single object
    def get(self, train_number):
        """Get a specific train by train number"""
        user_id = request.current_user.id
        train = Train.query.filter_by(train_number=train_number).first()
        if not train:
            api.abort(404, f"Train {train_number} not found")

        favourite_train_numbers = [fav.train_number for fav in UserFavouriteTrain.query.filter_by(user_id=user_id).all()]
        subscribed_train_numbers = [sub.train_number for sub in TrainSubscription.query.filter_by(user_id=user_id).all()]
        
        train_data = serialize_train(train, favourite_train_numbers, subscribed_train_numbers)

        return train_data