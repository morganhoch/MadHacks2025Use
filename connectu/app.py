from flask import Flask, redirect, url_for, session, render_template
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from dotenv import load_dotenv
import os, secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey123")

# ===== Step 1: Use server-side sessions (Flask-Session) =====
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SESSION_TYPE'] = 'filesystem'  # store session on disk
app.config['SESSION_FILE_DIR'] = os.path.join(basedir, 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True  # adds extra security
Session(app)

# ===== Blueprints and Models =====
from messaging_routes import messaging_bp
from models import db, User, DirectMessage  # Import from models.py
app.register_blueprint(messaging_bp)

# Database setup
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

db.init_app(app)

# Auth0 setup
oauth = OAuth(app)
auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

# ===== Models =====
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    subjects = db.Column(db.String(200))  # comma-separated subjects
    prerequisites = db.Column(db.Text)

# ===== Routes =====
@app.route("/")
def index():
    user = session.get('user')
    return render_template("index.html", user=user)

@app.route("/login")
def login():
    # Generate nonce and store in session
    session["nonce"] = secrets.token_urlsafe(16)
    redirect_uri = os.getenv("AUTH0_CALLBACK_URL")
    return auth0.authorize_redirect(redirect_uri=redirect_uri, nonce=session["nonce"])

@app.route("/callback")
def callback():
    # 1. Get token (DO NOT pass state or nonce)
    token = auth0.authorize_access_token()

    # 2. Validate ID token using the stored nonce
    userinfo = auth0.parse_id_token(token, nonce=session.get("nonce"))

    # 3. Save user in session
    session['user'] = {
        'auth0_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email']
    }

    # 4. Add user to DB if missing
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

# ===== Run App =====
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False, host="localhost")
