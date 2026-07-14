from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session,send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import firebase_admin
from firebase_admin import credentials,firestore

import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.exists(os.path.join(BASE_DIR, "firebase-key.json")):

    cred = credentials.Certificate(
        os.path.join(BASE_DIR, "firebase-key.json")
    )

else:

    firebase_json = os.environ.get("FIREBASE_KEY")

    cred = credentials.Certificate(
        json.loads(firebase_json)
    )

firebase_admin.initialize_app(cred)

db_firestore = firestore.client()


app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
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
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    quiz_id = db.Column(db.Integer)

    question = db.Column(db.String(300))

    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))

    correct = db.Column(db.String(10))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))
    created_by = db.Column(db.String(100))

class StudyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)

    minutes = db.Column(db.Integer)

    date = db.Column(db.String(20))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

    role = db.Column(db.String(20), default="student")

    xp = db.Column(db.Integer, default=0)

    streak = db.Column(db.Integer, default=0)

    daily_goal_minutes = db.Column(db.Integer, default=120)

    today_study_minutes = db.Column(db.Integer, default=0)

    total_study_minutes = db.Column(db.Integer, default=0)

    last_study_date = db.Column(db.String(50))


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_secret = db.Column(db.String(100), default="SCHOOL2026")

class PDF(db.Model):
 id = db.Column(db.Integer, primary_key=True)

title = db.Column(db.String(200))

filename = db.Column(db.String(300))

upload_date = db.Column(
    db.DateTime,
    default=datetime.utcnow
)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    content = db.Column(db.Text)

    teacher_name = db.Column(db.String(100))

    created_at = db.Column(
        db.String(100),
        default=str(datetime.now())
    )


class PDFFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200))

    filename = db.Column(db.String(300))

    uploaded_by = db.Column(db.String(100))

    upload_date = db.Column(
        db.String(100),
        default=str(datetime.now())
    )


# ---------------- CREATE TABLES ON START ----------------
with app.app_context():
    db.create_all()

    # create default settings if not exist
    if not Settings.query.first():
        db.session.add(Settings(teacher_secret="SCHOOL2026"))
        db.session.commit()


# ---------------- HELPERS ----------------

def update_streak(user):

    today = datetime.now().strftime("%Y-%m-%d")

    if user.last_study_date == today:

        return

    if user.last_study_date:

        last = datetime.strptime(
            user.last_study_date,
            "%Y-%m-%d"
        )

        diff = (datetime.now() - last).days

        if diff == 1:

            user.streak += 1

        else:

            user.streak = 1

    else:

        user.streak = 1

    user.last_study_date = today


def get_level(xp):

    if xp >= 5000:
        return 8

    elif xp >= 3500:
        return 7

    elif xp >= 2000:
        return 6

    elif xp >= 1000:
        return 5

    elif xp >= 500:
        return 4

    elif xp >= 250:
        return 3

    elif xp >= 100:
        return 2

    return 1


def get_rank(user_id):

    users = User.query.order_by(
        User.xp.desc()
    ).all()

    for index, user in enumerate(users):

        if user.id == user_id:
            return index + 1

    return "-"

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

    level = get_level(user.xp)

    rank = get_rank(user.id)

    return render_template(
        "student_dashboard.html",

        user=user,

        xp=user.xp,

        level=level,

        rank=rank,

        streak=user.streak,

        goal=user.daily_goal_minutes,

        today=user.today_study_minutes,

        total=user.total_study_minutes
    )



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


@app.route("/save_study_time", methods=["POST"])
def save_study_time():

    if "user_id" not in session:
        return "Login Required"

    minutes = int(request.form["minutes"])

    user = User.query.get(session["user_id"])

    # update study time
    user.today_study_minutes += minutes
    user.total_study_minutes += minutes

    # XP = study time
    user.xp += minutes

    # 🔥 update streak
    update_streak(user)
    log = StudyLog(
    user_id=user.id,
    minutes=minutes,
    date=datetime.now().strftime("%Y-%m-%d")
)

    db.session.add(log)
    # 🔥 bonus XP for streak
    if user.streak % 3 == 0:
        user.xp += 50

    db.session.commit()

    # firebase sync
    try:
        db_firestore.collection("users").document(
            str(user.id)
        ).update({
            "xp": user.xp,
            "streak": user.streak,
            "today_study_minutes": user.today_study_minutes,
            "total_study_minutes": user.total_study_minutes
        })

    except Exception as e:
        print(e)

    return "Saved"

@app.route("/notes")
def notes():

    all_notes = Note.query.order_by(
        Note.id.desc()
    ).all()

    return render_template(
        "notes.html",
        notes=all_notes
    )

@app.route("/create_note", methods=["GET", "POST"])
def create_note():

    if "user_id" not in session:
        return redirect("/teacher")

    user = User.query.get(session["user_id"])

    if user.role != "teacher":
        return "Access Denied"

    if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]

        note = Note(
            title=title,
            content=content,
            teacher_name=user.name
        )

        db.session.add(note)
        db.session.commit()

        try:

            db_firestore.collection("notes").document(
                str(note.id)
            ).set({

                "title": title,
                "content": content,
                "teacher_name": user.name

            })

        except Exception as e:

            print(e)

        return redirect("/notes")

    return render_template("create_note.html")


@app.route("/create_quiz", methods=["GET", "POST"])
def create_quiz():

    if "user_id" not in session:
        return redirect("/teacher")

    user = User.query.get(session["user_id"])

    if user.role != "teacher":
        return "Access Denied"

    if request.method == "POST":

        title = request.form["title"]

        quiz = Quiz(
            title=title,
            created_by=user.name
        )

        db.session.add(quiz)
        db.session.commit()

        return redirect("/add_question/" + str(quiz.id))

    return render_template("create_quiz.html")

@app.route("/add_question/<int:quiz_id>", methods=["GET", "POST"])
def add_question(quiz_id):

    if "user_id" not in session:
        return redirect("/teacher")

    if request.method == "POST":

        q = Question(
            quiz_id=quiz_id,
            question=request.form["question"],
            option_a=request.form["a"],
            option_b=request.form["b"],
            option_c=request.form["c"],
            option_d=request.form["d"],
            correct=request.form["correct"]
        )

        db.session.add(q)
        db.session.commit()

        return redirect("/add_question/" + str(quiz_id))

    return render_template("add_question.html", quiz_id=quiz_id)

@app.route("/quizzes")
def quizzes():

    all_quizzes = Quiz.query.all()

    return render_template(
        "quizzes.html",
        quizzes=all_quizzes
    )

@app.route("/attempt_quiz/<int:quiz_id>")
def attempt_quiz(quiz_id):

    questions = Question.query.filter_by(
        quiz_id=quiz_id
    ).all()

    return render_template(
        "attempt_quiz.html",
        questions=questions,
        quiz_id=quiz_id
    )

@app.route("/submit_quiz/<int:quiz_id>", methods=["POST"])
def submit_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/student")

    user = User.query.get(session["user_id"])

    questions = Question.query.filter_by(
        quiz_id=quiz_id
    ).all()

    score = 0

    for q in questions:

        answer = request.form.get(str(q.id))

        if answer == q.correct:
            score += 1

    xp_gain = score * 10

    user.xp += xp_gain

    db.session.commit()

    return render_template(
        "quiz_result.html",
        score=score,
        total=len(questions),
        xp=xp_gain
    )



@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect("/student")

    user_id = session["user_id"]

    logs = StudyLog.query.filter_by(
        user_id=user_id
    ).all()

    dates = []
    minutes = []

    for log in logs:
        dates.append(log.date)
        minutes.append(log.minutes)

    return render_template(
        "analytics.html",
        dates=dates,
        minutes=minutes
    )


@app.route("/pdfs")
def pdfs():

    if "user_id" not in session:
        return redirect("/student")

    all_pdfs = PDFFile.query.order_by(
        PDFFile.id.desc()
    ).all()

    return render_template(
        "pdfs.html",
        pdfs=all_pdfs
    )

@app.route("/upload_pdf", methods=["GET", "POST"])
def upload_pdf():

    if "user_id" not in session:
        return redirect("/teacher")

    user = User.query.get(session["user_id"])

    if not user or user.role != "teacher":
        return "Access Denied"

    if request.method == "POST":

        title = request.form["title"]

        pdf = request.files["pdf"]

        if pdf.filename == "":
            return "No file selected"

        filename = secure_filename(pdf.filename)

        save_path = os.path.join(
         app.config["UPLOAD_FOLDER"],
         "pdfs",
        filename)

        print("Saving PDF to:", save_path)

        pdf.save(save_path)

        pdf.save(
        os.path.join(
         app.config["UPLOAD_FOLDER"],
         "pdfs",
         filename))

        new_pdf = PDFFile(
            title=title,
            filename=filename,
            uploaded_by=user.name
        )

        db.session.add(new_pdf)
        db.session.commit()

        try:

            db_firestore.collection("pdfs").document(
                str(new_pdf.id)
            ).set({

                "title": title,
                "filename": filename,
                "uploaded_by": user.name

            })

        except Exception as e:

            print("Firestore Error:", e)

        return redirect("/pdfs")

    return render_template("upload_pdf.html")





@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/leaderboard")
def leaderboard():

    users = User.query.order_by(User.xp.desc()).all()

    return render_template(
        "leaderboard.html",
        users=users
    )


@app.route("/download_pdf/<filename>")
def download_pdf(filename):
 folder = os.path.join(
    app.config["UPLOAD_FOLDER"],
    "pdfs"
)

 print("Looking in folder:", folder)
 print("Looking for file:", filename)

 return send_from_directory(
    folder,
    filename,
    as_attachment=False
)




@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)