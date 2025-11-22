from test_messaging_app import app, db
from app import User  # or wherever User is defined

with app.app_context():
    # Create tables (if not already done)
    db.create_all()

    # Create test users
    user1 = User(auth0_id='test_auth0_user1', username="Student1", email="student1@example.com", role="student")
    user2 = User(auth0_id='test_auth0_user2', username="Tutor1", email="tutor1@example.com", role="tutor")
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    # Check their IDs and usernames
    print(user1.id, user2.id)
    print(user1.username, user2.username)
