from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import firebase_admin
from firebase_admin import credentials,firestore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

cred = credentials.Certificate(
    os.path.join(BASE_DIR, "firebase-key.json")
)

firebase_admin.initialize_app(cred)
db_firestore=firestore.client()


app = Flask(__name__)
app.secret_key = "studyhub_secret_key"

# ---------------- DATABASE FIX ----------------
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    database_url = "sqlite:///studyhub.db"
else:
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="student")
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_study_date = db.Column(db.String(50))


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_secret = db.Column(db.String(100), default="SCHOOL2026")


# ---------------- CREATE TABLES ON START ----------------
with app.app_context():
    db.create_all()

    # create default settings if not exist
    if not Settings.query.first():
        db.session.add(Settings(teacher_secret="SCHOOL2026"))
        db.session.commit()


# ---------------- HELPERS ----------------
def add_xp(user_id, points):
    user = User.query.get(user_id)
    if user:
        user.xp += points
        db.session.commit()


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

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return "Email already registered"

    # Save in SQLite
    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role="student"
    )

    db.session.add(user)
    db.session.commit()

    # Save in Firestore
    try:
        db_firestore.collection("users").document(str(user.id)).set({
            "name": name,
            "email": email,
            "role": "student",
            "xp": 0,
            "streak": 0
        })

        print("✅ Saved to Firestore")

    except Exception as e:
        print("❌ Firestore Error:", e)

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

    if "user_id" not in session:
        return redirect("/student")

    user = User.query.get(session["user_id"])

    return render_template(
        "student_dashboard.html",
        xp=user.xp
    )


@app.route("/add_xp")
def add_xp_route():

    if "user_id" not in session:
        return redirect("/student")

    user = User.query.get(session["user_id"])

    user.xp += 10

    db.session.commit()

    return redirect("/student_dashboard")






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
        return "Invalid Teacher Secret Code"

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

    try:
        db_firestore.collection("users").document(str(user.id)).set({
            "name": name,
            "email": email,
            "role": "teacher",
            "xp": 0,
            "streak": 0
        })

        print("✅ Teacher saved to Firestore")

    except Exception as e:
        print("❌ Firestore Error:", e)

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

    if "user_id" not in session:
        return redirect("/teacher")

    return render_template("teacher_dashboard.html")

@app.route("/leaderboard")
def leaderboard():

    users = User.query.order_by(User.xp.desc()).all()

    return render_template(
        "leaderboard.html",
        users=users
    )




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)