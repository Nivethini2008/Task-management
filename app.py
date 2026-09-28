from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="Pending")
    priority = db.Column(db.String(30), default="Medium")
    due_date = db.Column(db.String(20), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M") if task.updated_at else ""
    }


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=session["user_id"]).order_by(Task.id.desc()).all()
    return render_template(
        "dashboard.html",
        tasks=[task_to_dict(task) for task in tasks],
        user_name=session.get("user_name", "User")
    )


# ---------------- API: CRUD OPERATIONS ----------------

@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=session["user_id"]).order_by(Task.id.desc()).all()
    return jsonify([task_to_dict(task) for task in tasks])


@app.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    status = data.get("status", "Pending")
    priority = data.get("priority", "Medium")
    due_date = data.get("due_date", "")

    if not title:
        return jsonify({"error": "Task title is required."}), 400

    if status not in ["Pending", "In Progress", "Completed"]:
        return jsonify({"error": "Invalid status."}), 400

    if priority not in ["Low", "Medium", "High"]:
        return jsonify({"error": "Invalid priority."}), 400

    task = Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        user_id=session["user_id"]
    )
    db.session.add(task)
    db.session.commit()

    socketio.emit(
        "task_created",
        task_to_dict(task),
        room=f"user_{session['user_id']}"
    )

    return jsonify(task_to_dict(task)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(
        id=task_id,
        user_id=session["user_id"]
    ).first()

    if not task:
        return jsonify({"error": "Task not found."}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = data["title"].strip()
        if not title:
            return jsonify({"error": "Task title cannot be empty."}), 400
        task.title = title

    if "description" in data:
        task.description = data["description"].strip()

    if "status" in data:
        if data["status"] not in ["Pending", "In Progress", "Completed"]:
            return jsonify({"error": "Invalid status."}), 400
        task.status = data["status"]

    if "priority" in data:
        if data["priority"] not in ["Low", "Medium", "High"]:
            return jsonify({"error": "Invalid priority."}), 400
        task.priority = data["priority"]

    if "due_date" in data:
        task.due_date = data["due_date"]

    task.updated_at = datetime.utcnow()
    db.session.commit()

    socketio.emit(
        "task_updated",
        task_to_dict(task),
        room=f"user_{session['user_id']}"
    )

    return jsonify(task_to_dict(task))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(
        id=task_id,
        user_id=session["user_id"]
    ).first()

    if not task:
        return jsonify({"error": "Task not found."}), 404

    task_data = {"id": task.id}
    db.session.delete(task)
    db.session.commit()

    socketio.emit(
        "task_deleted",
        task_data,
        room=f"user_{session['user_id']}"
    )

    return jsonify({"message": "Task deleted successfully."})


@socketio.on("join")
def handle_join():
    if "user_id" in session:
        join_room(f"user_{session['user_id']}")


@app.context_processor
def inject_year():
    return {"current_year": datetime.now().year}


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="127.0.0.1", port=5000)
