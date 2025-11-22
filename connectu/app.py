from flask import Flask, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///connectu.db'
db = SQLAlchemy(app)

# Auth0 setup
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    api_base_url=f'https://{os.getenv("AUTH0_DOMAIN")}',
    access_token_url=f'https://{os.getenv("AUTH0_DOMAIN")}/oauth/token',
    authorize_url=f'https://{os.getenv("AUTH0_DOMAIN")}/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

# Database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auth0_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    role = db.Column(db.String(10))  # student or tutor
    bio = db.Column(db.Text)
    subjects = db.Column(db.String(200))

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
    else:
        return "Welcome to ConnectU! <a href='/login'>Login</a>"

@app.route("/login")
def login():
    return auth0.authorize_redirect(redirect_uri=os.getenv("AUTH0_CALLBACK_URL"))

@app.route("/callback")
def callback():
    token = auth0.authorize_access_token()
    userinfo = auth0.parse_id_token(token)
    
    session['user'] = {
        'auth0_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email']
    }

    # Check if user exists in DB, if not add
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
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?returnTo={url_for('home', _external=True)}&client_id={os.getenv('AUTH0_CLIENT_ID')}"
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


