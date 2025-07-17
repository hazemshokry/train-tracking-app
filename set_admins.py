# Run this script to set up admin users for Facebook group moderators
from app import create_app  # Import your app factory
from app.models.user_reliability import UserReliability
from app.extensions import db

# Create a Flask app instance
app = create_app()

# Use the app_context to work with the database
with app.app_context():
    # Replace with your actual admin user IDs
    admin_user_ids = [1, 2, 3]  # Your Facebook group moderators

    for user_id in admin_user_ids:
        reliability = UserReliability.get_or_create(user_id)
        reliability.user_type = 'admin'
        reliability.reliability_score = 1.0
        print(f"Set user {user_id} as admin")

    db.session.commit()
    print("Admin users configured!")