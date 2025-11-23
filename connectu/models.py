from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()
#35rUlj6WjkJKWT79AR8OR907AGg_36o9L39otApbaHZRsiJ8V GROK
#https://supernaturalistic-misha-multimacular.ngrok-free.dev/callback
#https://supernaturalistic-misha-multimacular.ngrok-free.dev
#http://localhost:5000/callback
#http://localhost:5000
# Association table for users joining courses -> Many to Many relationship
#user_courses = db.Table('user_courses',
#    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
#    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
#)

# Database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auth0_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    bio = db.Column(db.Text)
     # New fields
    availability = db.Column(db.String(100))  # e.g., "Mon 3-5pm, Wed 6-8pm"
    personal_links = db.Column(db.Text)  # Can store multiple links, separated by commas or newlines
    avatar_url = db.Column(db.String(200))  # <-- This stores the selected avatar
    user_courses = db.relationship('UserCourse', back_populates='user', lazy=True)


class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    students = db.relationship('UserCourse', back_populates='course', lazy=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref='questions', lazy=True)
    user = db.relationship('User', backref='questions', lazy=True)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship('Question', backref='answers', lazy=True)
    user = db.relationship('User', backref='answers', lazy=True)

class UserCourse(db.Model):
    __tablename__ = 'user_courses'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    term = db.Column(db.String(20), nullable=False)

    user = db.relationship('User', back_populates='user_courses')
    course = db.relationship('Course', back_populates='students')
