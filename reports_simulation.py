import random
from datetime import datetime, timedelta, timezone
from app import create_app
from app.models import UserReport, Train, Station, User, Route
from app.extensions import db
import time


from dotenv import load_dotenv
load_dotenv()

# Load the app with the correct configuration
app = create_app()

# Set up delay parameters
MIN_DELAY = timedelta(minutes=-15)
MAX_DELAY = timedelta(minutes=15)
TARGET_RECORDS = 3500  # Total target records

def generate_random_delay():
    """Generate a random delay within the specified range."""
    return timedelta(minutes=random.randint(-15, 15))

def generate_synthetic_report(train, route_entry, user, report_type):
    """Generate a synthetic report for a given train, route entry, user, and report type."""

    # Set the scheduled time based on report type
    if report_type == 'arrival':
        scheduled_time = route_entry.scheduled_arrival_time
    elif report_type == 'departure':
        # Use arrival time as fallback if departure time is missing
        scheduled_time = route_entry.scheduled_departure_time or route_entry.scheduled_arrival_time
    else:
        scheduled_time = route_entry.scheduled_arrival_time  # onboard/offboard can use arrival as a reference
    
    # Check if scheduled_time is None and skip this route entry if it is
    if scheduled_time is None:
        print(f"Skipping Route {route_entry.id} for Train {train.train_number} due to missing scheduled time.")
        return False
    
    # Convert the scheduled time to a timezone-aware datetime for manipulation
    scheduled_datetime = datetime.combine(datetime.today(), scheduled_time).replace(tzinfo=timezone.utc)
    
    # Add random delay within realistic limits (±15 minutes)
    reported_time = scheduled_datetime + generate_random_delay()
    
    # Avoid generating future times
    if reported_time > datetime.now(timezone.utc):
        reported_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 5))
    
    # Step 5: Create and save the synthetic report
    new_report = UserReport(
        user_id=user.id,
        train_number=train.train_number,
        station_id=route_entry.station_id,
        report_type=report_type,
        reported_time=reported_time,
        created_at=datetime.now(timezone.utc),  # Updated to timezone-aware
        is_valid=True  # Assume all synthetic data is valid
    )
    
    # Commit to the database
    db.session.add(new_report)
    db.session.commit()
    print(f"Generated report for train {train.train_number} at station {route_entry.station_id}.")
    return True

if __name__ == "__main__":
    with app.app_context():
        report_count = 0  # Initialize report counter
        users = User.query.all()
        if not users:
            print("No users found in the database.")
        else:
            user_count = len(users)
            
            # Loop over all trains to ensure diverse data
            trains = Train.query.all()
            while report_count < TARGET_RECORDS:
                for train in trains:
                    # Choose a random route entry for each report
                    route_entries = Route.query.filter_by(train_number=train.train_number).all()
                    if not route_entries:
                        print(f"No route entries found for train {train.train_number}.")
                        continue
                    
                    # Randomly select a route entry (station) for this report
                    route_entry = random.choice(route_entries)
                    user = random.choice(users)  # Select a random user
                    report_type = random.choice(['arrival', 'departure', 'onboard', 'offboard'])
                    
                    # Generate a synthetic report for the current train, route, and user
                    if generate_synthetic_report(train, route_entry, user, report_type):
                        report_count += 1
                    
                    # Stop if the target count is reached
                    if report_count >= TARGET_RECORDS:
                        break
                    
                    # Wait 1 second between each record generation
                    time.sleep(0.2)

            print(f"Finished generating {report_count} reports.")