from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from dotenv import load_dotenv
import os, secrets
from models import db, User, DirectMessage, Course, Question, Answer  # import all models at once
from messaging_routes import messaging_bp
from populate_courses import populate_courses


# ===== Load environment variables =====
load_dotenv()

# ===== Flask App Setup =====
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
# Use Railway Postgres
db_path = os.path.join(basedir, 'instance', 'connectu.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
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
    user_obj = None

    if 'user' in session:
        user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()

    if request.method == "POST":
        if not user_obj:
            flash("Please log in to post a question or answer.", "warning")
            return redirect(url_for("login"))
        
        content = request.form.get("content")
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

    # Get questions for this course
    questions = Question.query.filter_by(course_id=course.id).order_by(Question.timestamp.desc()).all()
    
    # THIS IS THE NEW LINE: get users enrolled in the course
    enrolled_users = course.students  # 'students' comes from your backref in models

    return render_template(
        "course_detail.html",
        course=course,
        questions=questions,
        user=user_obj,
        enrolled_users=enrolled_users
    )

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    cleaned = query.replace("|", "").strip().upper()
    results = Course.query.filter(Course.course_code.like(f"%{cleaned}%")).all()
    user_obj = None
    if 'user' in session:
        user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    return render_template("search.html", query=query, results=results, user=user_obj)

@app.route("/leave_course/<int:course_id>", methods=['POST'])
def leave_course(course_id):
    if 'user' not in session:
        flash("You must be logged in to leave a course.")
        return redirect(url_for('login'))
    user = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    course = Course.query.get_or_404(course_id)
    if course in user.courses:
        user.courses.remove(course)
        db.session.commit()
        flash(f"You have left {course.course_code}.", "info")
    else:
        flash("You are not enrolled in this course.", "warning")
    return redirect(url_for('course_detail', course_code=course.course_code))


@app.route("/profile")
def profile():
    user_session = session.get("user")
    if not user_session:
        flash("Please sign in to view your profile.", "warning")
        return redirect(url_for("login"))

    user = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("index"))

    return render_template("profile.html", user=user, user_courses=user.courses)

@app.route("/profile/<int:user_id>", endpoint="profile_view")
def profile_view(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("profile.html", user=user, user_courses=user.courses)

@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user_session = session.get("user")
    if not user_session:
        flash("Please sign in to edit your profile.", "warning")
        return redirect(url_for("login"))

    user = User.query.filter_by(auth0_id=user_session["auth0_id"]).first()
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        user.username = request.form.get("username", user.username)
        user.bio = request.form.get("bio", user.bio)
        user.subjects = request.form.get("subjects", user.subjects)
        db.session.commit()
        session["user"]["name"] = user.username
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user)

@app.route("/join_course/<int:course_id>", methods=['POST'])
def join_course(course_id):
    if 'user' not in session:
        flash("You must be logged in to join a course.")
        return redirect(url_for('login'))

    user = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    course = Course.query.get_or_404(course_id)

    if course in user.courses:
        flash("You have already joined this course.")
    else:
        user.courses.append(course)
        db.session.commit()
        flash(f"You have joined {course.course_code}!")

    return redirect(request.referrer or url_for('search'))

# ===== Run App =====
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        populate_courses()
    app.run()

