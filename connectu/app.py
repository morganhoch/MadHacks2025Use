from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from dotenv import load_dotenv
import os, secrets
from models import db, User, DirectMessage, Course, Question, Answer  # import all models at once
from messaging_routes import messaging_bp
from populate_courses import populate_courses
from flask_ngrok import run_with_ngrok

# ===== Load environment variables =====
load_dotenv()

# ===== Flask App Setup =====
app = Flask(__name__)
run_with_ngrok(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey123")

# ===== Session Setup =====
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(basedir, 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# ===== Database Setup =====
# Use Railway Postgres
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")  # Railway DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ===== Register blueprints =====
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
    user_session = session.get("user")
    user_obj = None
    user_courses = []
    if user_session:
        user_obj = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
        if user_obj:
            user_courses = user_obj.courses
    return render_template("index.html", user=user_obj, user_courses=user_courses)

@app.route("/login")
def login():
    session["nonce"] = secrets.token_urlsafe(16)
    redirect_uri = os.getenv("AUTH0_CALLBACK_URL")
    return auth0.authorize_redirect(redirect_uri=redirect_uri, nonce=session["nonce"])

@app.route("/callback")
def callback():
    token = auth0.authorize_access_token()
    userinfo = auth0.parse_id_token(token, nonce=session.get("nonce"))

    # Store user in session
    session["user"] = {
        "auth0_id": userinfo["sub"],
        "name": userinfo["name"],
        "email": userinfo["email"]
    }

    # Add to DB if user doesn't exist
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"https://{os.getenv('AUTH0_DOMAIN')}/v2/logout?"
        f"returnTo={url_for('index', _external=True)}&"
        f"client_id={os.getenv('AUTH0_CLIENT_ID')}"
    )

@app.route("/inbox")
def inbox():
    return render_template("inbox.html")

@app.route("/course/<course_code>", methods=["GET", "POST"])
def course_detail(course_code):
    course = Course.query.filter_by(course_code=course_code).first_or_404()

    if request.method == "POST":
        user_session = session.get("user")
        if not user_session:
            flash("Please log in to post a question or answer.", "warning")
            return redirect(url_for("login"))
        
        content = request.form.get("content")
        user_obj = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
        if "question" in request.form:
            new_question = Question(course_id=course.id, user_id=user_obj.id, content=content)
            db.session.add(new_question)
        elif "answer" in request.form:
            question_id = int(request.form.get("question_id"))
            new_answer = Answer(question_id=question_id, user_id=user_obj.id, content=content)
            db.session.add(new_answer)
        db.session.commit()
        flash("Your post has been added.", "success")
        return redirect(url_for("course_detail", course_code=course_code))

    questions = Question.query.filter_by(course_id=course.id).order_by(Question.timestamp.desc()).all()
    return render_template("course_detail.html", course=course, questions=questions)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    cleaned = query.replace("|", "").strip().upper()
    results = Course.query.filter(Course.course_code.like(f"%{cleaned}%")).all()
    user_obj = None
    if 'user' in session:
        user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    return render_template("search.html", query=query, results=results, user=user_obj)

@app.route("/profile")
def profile
