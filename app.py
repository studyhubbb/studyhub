from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "studyhub_secret_key"

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    database_url = "sqlite:///studyhub.db"
else:
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# AUTO CREATE TABLES
with app.app_context():
    db.create_all()

# ---------------- USERS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default="student")
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_study_date = db.Column(db.String(50))


# ---------------- SETTINGS ----------------
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_secret = db.Column(db.String(100), default="SCHOOL2026")


# ---------------- HELPERS ----------------
def add_xp(user_id, points):
    user = User.query.get(user_id)
    if user:
        user.xp += points
        db.session.commit()

def get_level(xp):
    return (xp // 100) + 1


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect("/student")


@app.route("/student")
def student():
    return render_template("student_login.html")


@app.route("/student_register", methods=["POST"])
def student_register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    if User.query.filter_by(email=email).first():
        return "Email already registered"

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role="student"
    )

    db.session.add(user)
    db.session.commit()

    return redirect("/student")


@app.route("/student_login", methods=["POST"])
def student_login():
    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email, role="student").first()

    if user and check_password_hash(user.password, password):
        session["user_id"] = user.id
        return redirect("/student_dashboard")

    return "Invalid login"


@app.route("/student_dashboard")
def student_dashboard():
    return render_template("student_dashboard.html")


@app.route("/teacher")
def teacher():
    return render_template("teacher_login.html")


@app.route("/teacher_register", methods=["POST"])
def teacher_register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    code = request.form["secret_code"]

    setting = Settings.query.first()
    if not setting:
        return "System not configured"

    if code != setting.teacher_secret:
        return "Invalid code"

    if User.query.filter_by(email=email).first():
        return "Email already registered"

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role="teacher"
    )

    db.session.add(user)
    db.session.commit()

    return redirect("/teacher")


@app.route("/teacher_login", methods=["POST"])
def teacher_login():
    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email, role="teacher").first()

    if user and check_password_hash(user.password, password):
        session["user_id"] = user.id
        return redirect("/teacher_dashboard")

    return "Invalid login"


@app.route("/teacher_dashboard")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)