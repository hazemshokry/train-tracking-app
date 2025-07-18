import random
from datetime import datetime, timedelta
from app.models import UserReport, Train, Route, User, Operation
from app.extensions import db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_all_trains():
    """Retrieve all available trains."""
    return db.session.query(Train.train_number).all()

def get_route_for_train(train_number):
    """Retrieve route stations and scheduled times for a specific train, ordered by sequence."""
    return db.session.query(Route.station_id, Route.scheduled_departure_time, Route.scheduled_arrival_time).\
        filter(Route.train_number == train_number).\
        order_by(Route.sequence_number).all()

def get_all_users():
    """Retrieve all available users to assign reports."""
    return db.session.query(User.id).all()

def get_or_create_operation(train_number, operational_date):
    """Retrieve or create an Operation entry for the given train and date."""
    operation = db.session.query(Operation).filter_by(train_number=train_number, operational_date=operational_date).first()
    if not operation:
        operation = Operation(
            train_number=train_number,
            operational_date=operational_date,
            status="on time"
        )
        db.session.add(operation)
        db.session.flush()  # Ensures operation.id is available without committing
    return operation

def insert_synthetic_data(app, num_reports=10, train_number=None, user_id=None):
    """Insert synthetic user reports with accumulated delay for a random subset of stations on each train's route."""
    with app.app_context():
        # Get all trains and filter if a specific train_number is provided
        if train_number:
            # Explicitly filter to get only the specific train
            trains = db.session.query(Train).filter_by(train_number=train_number).all()
        else:
            trains = get_all_trains()
        
        # Get all users and filter if a specific user_id is provided
        users = [user for user in get_all_users() if not user_id or user.id == user_id]
        
        for train in trains:
            train_number = train.train_number
            full_route = get_route_for_train(train_number)
            
            if len(full_route) > 1:
                num_stations = random.randint(1, len(full_route))
                selected_stations = random.sample(full_route, num_stations)
                selected_stations.sort(key=lambda x: full_route.index(x))
            else:
                selected_stations = full_route
            
            accumulated_delay = timedelta(minutes=0)
            report_count = 0  # Reset the report count for each train
            
            # Set operational date to today's date (or adjust as needed)
            operational_date = datetime.today().date()
            operation = get_or_create_operation(train_number, operational_date)
            
            for station in selected_stations:
                if report_count >= num_reports:
                    break
                
                station_id, scheduled_departure, scheduled_arrival = station
                report_type = random.choice(['arrival', 'departure', 'onboard', 'offboard', 'delay', 'cancelled', 'passed_station'])
                base_time = scheduled_arrival if report_type == 'arrival' and scheduled_arrival else scheduled_departure
                
                if not base_time:
                    continue
                
                additional_delay = timedelta(minutes=random.randint(1, 10))
                accumulated_delay += additional_delay
                reported_time = datetime.combine(datetime.today(), base_time) + accumulated_delay
                
                selected_user_id = random.choice(users).id if users else None
                if selected_user_id is None:
                    continue
                
                new_report = UserReport(
                    user_id=selected_user_id,
                    train_number=train_number,
                    operation_id=operation.id,
                    station_id=station_id,
                    report_type=report_type,
                    reported_time=reported_time,
                    is_valid=True,
                    confidence_score=round(random.uniform(0.6, 0.95), 2)
                )
                
                db.session.add(new_report)
                report_count += 1

        db.session.commit()