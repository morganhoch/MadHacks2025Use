from flask import Flask, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os, secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey123")

from messaging_routes import messaging_bp
from models import db, User, DirectMessage  # Import from models.py
app.register_blueprint(messaging_bp)

# Database setup
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'connectu.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auth0_id = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100))
    role = db.Column(db.String(50))

# Auth0 setup
oauth = OAuth(app)
auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    subjects = db.Column(db.String(200))  # comma-separated subjects
    prerequisites = db.Column(db.Text)
# Routes
@app.route("/")
def home():
    user = session.get('user')
    if user:
        return f"Hello, {user['name']}! <a href='/logout'>Logout</a>"
    return "Welcome! <a href='/login'>Login</a>"

@app.route("/login")
def login():
    # Generate nonce and store in session
    session["nonce"] = secrets.token_urlsafe(16)
    redirect_uri = os.getenv("AUTH0_CALLBACK_URL")
    return auth0.authorize_redirect(redirect_uri=redirect_uri, nonce=session["nonce"])

@app.route("/callback")
def callback():
    token = auth0.authorize_access_token(nonce=session.get("nonce"))
    userinfo = auth0.parse_id_token(token, nonce=session.get("nonce"))

    session['user'] = {
        'auth0_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email']
    }

    # Add user to DB if not exists
    user = User.query.filter_by(auth0_id=userinfo['sub']).first()
    if not user:
        user = User(
            auth0_id=userinfo['sub'],
            username=userinfo['name'],
            email=userinfo['email'],
            role='student'
        )
        db.session.add(user)
        db.session.commit()

    return redirect(url_for('home'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?"
        f"returnTo={url_for('home', _external=True)}&client_id={os.getenv('AUTH0_CLIENT_ID')}"
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False)

