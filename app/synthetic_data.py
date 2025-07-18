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

def insert_synthetic_data(app, num_reports=10, train_number=None):
    """Insert synthetic user reports with a realistic, accumulating delay."""
    with app.app_context():
        if train_number:
            trains = db.session.query(Train).filter_by(train_number=train_number).all()
        else:
            trains = get_all_trains()

        users = get_all_users()
        if not users:
            print("No users found. Cannot generate reports.")
            return

        for train in trains:
            train_number = train.train_number
            full_route = get_route_for_train(train_number)
            if not full_route:
                continue

            # Create a list of 'num_reports' station events to generate
            report_events = random.choices(full_route, k=num_reports)
            
            # *** THE FIX IS HERE ***
            # Sort the events by their actual sequence in the route to ensure chronological processing.
            report_events.sort(key=lambda s: full_route.index(s))

            total_accumulated_delay = timedelta(minutes=0)
            operational_date = datetime.today().date()
            operation = get_or_create_operation(train_number, operational_date)

            for event_station in report_events:
                station_id, scheduled_departure, scheduled_arrival = event_station

                # Add a small, positive delay for each step in the journey
                total_accumulated_delay += timedelta(minutes=random.randint(2, 10))
                
                base_time = scheduled_arrival or scheduled_departure
                if not base_time:
                    continue

                reported_time = datetime.combine(operational_date, base_time) + total_accumulated_delay
                
                new_report = UserReport(
                    user_id=random.choice(users).id,
                    train_number=train_number,
                    operation_id=operation.id,
                    station_id=station_id,
                    report_type=random.choice(['arrival', 'departure', 'onboard', 'offboard']),
                    reported_time=reported_time,
                    is_valid=True,
                    confidence_score=round(random.uniform(0.6, 0.95), 2)
                )
                db.session.add(new_report)

        db.session.commit()