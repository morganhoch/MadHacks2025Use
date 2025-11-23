from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

# Database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auth0_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    bio = db.Column(db.Text)
    subjects = db.Column(db.String(200))

class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages', lazy=True)
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(10), default='pending')  # 'pending', 'accepted', 'denied'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: relationships for easier querying
    requester = db.relationship('User', foreign_keys=[requester_id])
    requested = db.relationship('User', foreign_keys=[requested_id])
