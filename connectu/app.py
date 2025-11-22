from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import request, redirect, url_for

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to ConnectU!"

if __name__ == "__main__":
    app.run(debug=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///connectu.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'student' or 'tutor'
    bio = db.Column(db.Text)
    subjects = db.Column(db.String(200))  # comma-separated list


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]
        bio = request.form["bio"]
        subjects = request.form["subjects"]

        user = User(username=username, email=email, role=role, bio=bio, subjects=subjects)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("home"))

    return '''
        <form method="post">
            Username: <input name="username"><br>
            Email: <input name="email"><br>
            Role: <input name="role" placeholder="student or tutor"><br>
            Bio: <textarea name="bio"></textarea><br>
            Subjects: <input name="subjects"><br>
            <input type="submit">
        </form>
    '''


