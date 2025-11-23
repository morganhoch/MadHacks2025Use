from flask import Flask, redirect, url_for, session, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from flask_session import Session
from dotenv import load_dotenv
import os, secrets
from models import db, User, DirectMessage, Course, Question, Answer, UserCourse
from messaging_routes import messaging_bp
from populate_courses import populate_courses
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, Course, Document, User


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

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
# ===== Database Setup =====
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
            user_courses = [uc.course for uc in user_obj.user_courses]
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

@app.route("/course/<course_code>", methods=["GET", "POST"])
def course_detail(course_code):
    course = Course.query.filter_by(course_code=course_code).first_or_404()
    user_obj = None

    if 'user' in session:
        user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()

    if request.method == "POST" and user_obj:
        # Handle new question
        if "question" in request.form:
            content = request.form.get("content")
            if content:
                q = Question(course_id=course.id, user_id=user_obj.id, content=content)
                db.session.add(q)
                db.session.commit()
                flash("Question posted!", "success")
                return redirect(url_for("course_detail", course_code=course.course_code))

        # Handle new answer
        if "answer" in request.form:
            content = request.form.get("content")
            question_id = request.form.get("question_id")
            if content and question_id:
                a = Answer(question_id=question_id, user_id=user_obj.id, content=content)
                db.session.add(a)
                db.session.commit()
                flash("Answer posted!", "success")
                return redirect(url_for("course_detail", course_code=course.course_code))
                
    # Existing Q&A logic
    questions = Question.query.filter_by(course_id=course.id).order_by(Question.timestamp.desc()).all()
    # enrolled_users = [uc.user for uc in course.students]  # this is a list of UserCourse objects
    enrolled_users = course.students
    
    return render_template(
        "course_detail.html",
        course=course,
        questions=questions,
        user=user_obj,
        enrolled_users=enrolled_users,  # okay to keep, just use uc.user in template
    )


@app.route("/remove_question/<int:question_id>", methods=["POST"])
def remove_question(question_id):
    # Make sure user is logged in
    if "user" not in session:
        flash("You must be logged in to remove a question.", "danger")
        return redirect(request.referrer or "/")

    question = Question.query.get_or_404(question_id)
    user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    if question.user_id != user_obj.id:
        flash("You can only remove your own questions.", "danger")
        return redirect(url_for('course_detail', course_code=question.course.course_code))
    
    course_code = question.course.course_code
    
    db.session.delete(question)
    db.session.commit()
    flash("Your question has been removed.", "success")
    return redirect(url_for('course_detail', course_code=question.course.course_code))

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
        flash("You must be logged in to leave a course.", "warning")
        return redirect(url_for('login'))

    user = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    course = Course.query.get_or_404(course_id)

    uc = UserCourse.query.filter_by(user_id=user.id, course_id=course.id).first()
    if uc:
        db.session.delete(uc)
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

    return render_template("profile.html", user=user, user_courses=user.user_courses)


@app.route("/profile/<int:user_id>", endpoint="profile_view")
def profile_view(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("profile.html", user=user, user_courses=[uc.course for uc in user.user_courses])


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
        available_times = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            available_times[day] = request.form.getlist(f"available_times[{day}][]") or []

        user.available_times = available_times
        user.personal_links = request.form.get("personal_links", user.personal_links)
        user.avatar_url = request.form.get("avatar_url", user.avatar_url)
        db.session.commit()
        session["user"]["name"] = user.username
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    # For GET request, render the form
    return render_template("edit_profile.html", user=user)



@app.route("/join_course/<int:course_id>", methods=['POST'])
def join_course(course_id):
    if 'user' not in session:
        flash("You must be logged in to join a course.", "warning")
        return redirect(url_for('login'))

    # Get user and course
    user = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    course = Course.query.get_or_404(course_id)

    # Get status and term from the form
    status = request.form.get('status')
    term = request.form.get('term')

    if not status or not term:
        flash("Please select both status and term.", "warning")
        return redirect(request.referrer or url_for('course_detail', course_code=course.course_code))

    # Check if user is already enrolled
    existing = UserCourse.query.filter_by(user_id=user.id, course_id=course.id).first()
    if existing:
        flash("You have already joined this course.", "info")
    else:
        # Add the association object
        uc = UserCourse(user_id=user.id, course_id=course.id, status=status, term=term)
        db.session.add(uc)
        db.session.commit()
        flash(f"You joined {course.course_code} as a {status} for {term}!", "success")

    return redirect(request.referrer or url_for('course_detail', course_code=course.course_code))

@app.route('/course/<int:course_id>/upload', methods=['POST'])
def upload_document(course_id):
    if 'user' not in session:
        flash("You must be logged in to upload documents.", "warning")
        return redirect(request.referrer)

    file = request.files.get('document')
    if not file or file.filename == '':
        flash('No file selected', 'warning')
        return redirect(request.referrer)

   if allowed_file(file.filename):
    filename = secure_filename(file.filename)

    # Make sure folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    user_obj = User.query.filter_by(auth0_id=session['user']['auth0_id']).first()
    new_doc = Document(filename=filename, filepath=filepath, course_id=course_id, user_id=user_obj.id)
    db.session.add(new_doc)
    db.session.commit()

        flash('Document uploaded successfully!', 'success')

        course = Course.query.get_or_404(course_id)
        return redirect(url_for('course_detail', course_code=course.course_code))
    else:
        flash('Invalid file type', 'warning')
        return redirect(request.referrer)


# ===== Run App =====
if __name__ == "__main__":
    with app.app_context():
        xml_file = os.path.join(os.path.dirname(__file__), "courses_sitemap.xml")
        db.create_all()
        populate_courses(app, xml_file)  # populate courses from XML
    app.run()
