from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from dotenv import load_dotenv
import os, secrets
from models import db, User, DirectMessage, Course  # if you're using models.py
from messaging_routes import messaging_bp

# Load env variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey123")

# ===== Session Setup =====
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(basedir, 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# ===== Database Setup =====
db_path = os.path.join(basedir, 'instance', 'connectu.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # IMPORTANT
app.register_blueprint(messaging_bp)

# ===== OAuth / Auth0 Setup =====
oauth = OAuth(app)
auth0 = oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

# ===== Routes =====
@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)

@app.route("/login")
def login():
    session["nonce"] = secrets.token_urlsafe(16)
    redirect_uri = os.getenv("AUTH0_CALLBACK_URL")
    return auth0.authorize_redirect(redirect_uri=redirect_uri, nonce=session["nonce"])

@app.route("/inbox")
def inbox():
    return render_template("inbox.html")

@app.route("/courses/<course_code>")
def course_detail(course_code):
    # Look up the course by code
    course = Course.query.filter_by(course_code=course_code).first_or_404()
    return render_template("course_detail.html", course=course)

@app.route("/callback")
def callback():
    token = auth0.authorize_access_token()

    # Validate token with stored nonce
    userinfo = auth0.parse_id_token(token, nonce=session.get("nonce"))

    # Store user in session
    session["user"] = {
        "auth0_id": userinfo["sub"],
        "name": userinfo["name"],
        "email": userinfo["email"]
    }

    # Add to DB if they don't exist
    existing = User.query.filter_by(auth0_id=userinfo["sub"]).first()
    if not existing:
        new_user = User(
            auth0_id=userinfo["sub"],
            username=userinfo["name"],
            email=userinfo["email"],
            bio="",
            subjects=""
        )
        db.session.add(new_user)
        db.session.commit()

    return redirect(url_for("index"))

@app.route("/profile")
def profile():
    user_session = session.get("user")
    if not user_session:
        flash("Please sign in to view your profile.", "warning")
        return redirect(url_for("login"))

    # Fetch latest info from database
    user = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("index"))

    return render_template("profile.html", user=user)


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    # Make sure user is logged in
    user_session = session.get("user")
    if not user_session:
        flash("Please sign in to edit your profile.", "warning")
        return redirect(url_for("login"))

    # Fetch user from DB
    user = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        # Update user info
        user.username = request.form.get("username", user.username)
        user.bio = request.form.get("bio", user.bio)
        user.subjects = request.form.get("subjects", user.subjects)
        
        db.session.commit()  # Save changes

        # Update session info
        session["user"]["name"] = user.username
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    # Render form for GET request
    return render_template("edit_profile.html", user=user)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    # Normalize query
    cleaned = query.replace("|", "").strip().upper()

    # Search with OR conditions
    results = Course.query.filter(
        Course.course_code.like(f"%{cleaned}%")
    ).all()

    return render_template("search.html", query=query, results=results)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?"
        f"returnTo={url_for('index', _external=True)}&"
        f"client_id={os.getenv('AUTH0_CLIENT_ID')}"
    )

# ===== Run App =====
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

