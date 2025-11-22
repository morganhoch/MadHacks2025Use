from flask import Flask
from app import db, User  # Import your models
from messages import DirectMessage  # Your messaging model
from messaging_routes import messaging_bp  # Your blueprint

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'  # Use a test database!
app.config['SECRET_KEY'] = 'test'
db.init_app(app)

app.register_blueprint(messaging_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000)
