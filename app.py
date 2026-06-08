from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import session

app = Flask(__name__)
app.secret_key = "studyhub_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studyhub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    db.create_all()


# ---------------- USERS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20), default="student")  # student/teacher/admin
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_study_date = db.Column(db.String(50))


# ---------------- SETTINGS ----------------
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_secret = db.Column(db.String(100), default="SCHOOL2026")


# ---------------- SUBJECTS ----------------
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    name = db.Column(db.String(100))


# ---------------- STUDY SESSIONS ----------------
class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    minutes = db.Column(db.Integer)
    date = db.Column(db.String(50))


# ---------------- NOTES ----------------
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    filename = db.Column(db.String(255))
    date = db.Column(db.String(50))


# ---------------- CHAT ----------------
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    message = db.Column(db.Text)
    time = db.Column(db.String(50))


# ---------------- QUIZ ----------------
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    xp_reward = db.Column(db.Integer, default=50)


class QuizScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    score = db.Column(db.Integer)


# ---------------- GOALS ----------------
class DailyGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    hours = db.Column(db.Integer)


# ---------------- TODO ----------------
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    task = db.Column(db.String(255))
    done = db.Column(db.Boolean, default=False)


def add_xp(user_id, points):
    user = User.query.get(user_id)

    if user:
        user.xp += points
        db.session.commit()

def get_level(xp):
    return (xp // 100) + 1



# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/student")


# ---------------- STUDENT PAGES ----------------
@app.route("/student")
def student_login():
    return render_template("student_login.html")


@app.route("/student_register", methods=["POST"])
def student_register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    if User.query.filter_by(email=email).first():
        return "Email already exists"

    user = User(name=name, email=email, password=password, role="student")
    db.session.add(user)
    db.session.commit()

    return redirect("/student")


@app.route("/student_login", methods=["POST"])
def student_login_post():
    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email, password=password, role="student").first()

    if user:
        session["user_id"] = user.id
        session["role"]=user.role
        return redirect("/student_dashboard")

    return "Invalid Student Login"


@app.route("/student_dashboard")
def student_dashboard():
    return render_template("student_dashboard.html")


# ---------------- TEACHER ----------------
@app.route("/teacher")
def teacher_login():
    return render_template("teacher_login.html")


@app.route("/teacher_register", methods=["POST"])
def teacher_register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    secret = request.form["secret"]

    setting = Settings.query.first()

    if not setting or secret != setting.teacher_secret:
        role = "student"
    else:
        role = "teacher"

    user = User(name=name, email=email, password=password, role=role)
    db.session.add(user)
    db.session.commit()

    return redirect("/teacher")


@app.route("/teacher_login", methods=["POST"])
def teacher_login_post():
    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email, password=password, role="teacher").first()

    if user:
        session["user_id"] = user.id
        session["role"]=user.role
        return redirect("/teacher_dashboard")

    return "Invalid Teacher Login"


@app.route("/teacher_dashboard")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")


# ---------------- LEADERBOARD ----------------
@app.route("/leaderboard")
def leaderboard():
    users = User.query.order_by(User.xp.desc()).all()
    return render_template("leaderboard.html", users=users,get_level=get_level)


# ---------------- NOTES PAGE ----------------
@app.route("/notes")
def notes():
    return render_template("notes.html")


# ---------------- CHAT PAGE ----------------
@app.route("/chat")
def chat():
    return render_template("chat.html")


# ---------------- QUIZ PAGE ----------------
@app.route("/quiz")
def quiz():
    return render_template("quiz.html")


# ---------------- GOALS ----------------
@app.route("/goals")
def goals():
    return render_template("goals.html")


# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    users = User.query.all()
    return render_template("admin.html", users=users)


# ---------------- SETTINGS CHANGE ----------------
@app.route("/change_secret", methods=["POST"])
def change_secret():
    new_secret = request.form["secret"]

    setting = Settings.query.first()
    setting.teacher_secret = new_secret
    db.session.commit()

    return "Secret Updated"

@app.route("/save_timer", methods=["POST"])
def save_timer():

    subject = request.form["subject"]
    minutes = request.form["minutes"]

    user = User.query.get(session["user_id"])
    today = str(datetime.now().date())

    # STREAK LOGIC
    if user.last_study_date == today:
        pass
    elif user.last_study_date is None:
        user.streak = 1
    else:
        user.streak += 1

    user.last_study_date = today

    session_data = StudySession(
        user_id=user.id,
        subject=subject,
        minutes=int(minutes),
        date=today
    )

    db.session.add(session_data)

    add_xp(user.id, 10)

    db.session.commit()

    return "Saved + XP + Streak updated"


@app.route("/send_message", methods=["POST"])
def send_message():

    message = request.form["message"]

    new_msg = Message(
        user_id=session["user_id"],
        message=message,
        time=str(datetime.now())
    )

    db.session.add(new_msg)
    db.session.commit()

    return "sent"

@app.route("/get_messages")
def get_messages():

    messages = Message.query.all()

    return {
        "messages": [
            {
                "message": m.message,
                "user_id": m.user_id,
                "time": m.time
            }
            for m in messages
        ]
    }

@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():

    score = int(request.form["score"])
    quiz_id = request.form["quiz_id"]

    new_score = QuizScore(
        quiz_id=quiz_id,
        user_id=session["user_id"],
        score=score
    )

    db.session.add(new_score)

    # XP reward
    add_xp(session["user_id"], score * 5)

    db.session.commit()

    return "Quiz submitted + XP added"


# ---------------- CREATE DB ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not Settings.query.first():
            db.session.add(Settings(teacher_secret="SCHOOL2026"))
            db.session.commit()

    app.run(debug=True)