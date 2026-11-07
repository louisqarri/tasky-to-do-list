from datetime import date
from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from stats import build_stats
from charts import status_chart, user_chart
import pandas as pd
import os
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()
API_KEY = os.environ.get("API_KEY")

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///fallback.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    tasks: Mapped[list["Tasks"]] = relationship("Tasks", back_populates="user")

class Tasks(db.Model):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(255))
    priority: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(255))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["Users"] = relationship("Users", back_populates="tasks")

    def to_dict(self):
        dictionary = {}
        for colunm in self.__table__.columns:
            value = getattr(self, colunm.name)

            if isinstance(value, date):
                value = value.isoformat()

            dictionary[colunm.name] = value
        return dictionary

class TaskForm(FlaskForm):
    title = StringField("Task Title", validators=[DataRequired()])
    description = TextAreaField("Task Description", validators=[DataRequired()])
    priority =  SelectField("Priority",
                            choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                            default="medium")
    due_date =  DateField("Due date", validators=[Optional()])
    submit = SubmitField("Add Task")

def manager_only(func):
    @wraps(func)
    def wrapper_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_manager == True:
            return func(*args, **kwargs)
        else:
            return abort(403)
    return wrapper_function

def get_own_task(task_id):
    task = db.get_or_404(Tasks, task_id)
    if task.user_id != current_user.id and not current_user.is_manager:
        abort(403)
    return task

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/board")
@login_required
def board():
    if current_user.is_manager:
        all_tasks = db.session.execute(db.select(Tasks)).scalars().all()
    else:
        all_tasks = db.session.execute(db.select(Tasks).where(Tasks.user_id == current_user.id)).scalars().all()
    return render_template("board.html", tasks=all_tasks, today=date.today())

@app.route("/task-form", methods=["GET", "POST"])
@login_required
def task_form():
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Tasks(
            user_id = current_user.id,
            title = form.title.data,
            description = form.description.data,
            priority =  form.priority.data,
            due_date =  form.due_date.data,
            status = "todo"
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for("board"))
    return render_template("task_form.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.session.execute(db.select(Users).where(Users.email == email)).scalar()

        if not user:
            flash("This user does not exist, please try again.")
            return render_template("login.html")
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("board"))
        else:
            flash("Wrong password. Please try again.")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        email = request.form.get("email")
        name = request.form.get("name")
        existing_user = db.session.execute(db.select(Users).where(Users.email == email)).scalar()

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("register.html", email=request.form.get("email"))

        if existing_user:
            flash("This email is already registered. Please log in.")
            return redirect(url_for("login"))
        
        if confirm_password == password:
            new_user = Users(
                        password=generate_password_hash(password,
                                                        method='pbkdf2:sha256',
                                                        salt_length=8),
                        email = email,
                        name = name)

            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("board"))
        else:
            flash("The passwords dont match. Please try again.")
            return render_template("register.html", email=request.form.get("email"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/move/<int:task_id>/<direction>", methods=["POST"])
@login_required
def move(task_id, direction):
    status_list = ["todo", "inprogress", "done"]
    current_task = get_own_task(task_id)
    index = status_list.index(current_task.status)

    if direction == "right":
        index += 1
    elif direction == "left":
        index -= 1

    if 0 <= index < len(status_list):
        current_task.status = status_list[index]

    db.session.commit()
    return redirect(url_for("board"))

@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task_to_edit = get_own_task(task_id)
    form = TaskForm(obj=task_to_edit)
    form.submit.label.text = "Save Changes"
    if form.validate_on_submit():
        task_to_edit.title = form.title.data
        task_to_edit.description = form.description.data
        task_to_edit.priority = form.priority.data
        task_to_edit.due_date = form.due_date.data
        db.session.commit()
        return redirect(url_for("board"))
    return render_template("task_form.html", form=form, edit_mode=True)

@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete(task_id):
    task_to_delete = get_own_task(task_id)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for("board"))

@app.route("/manager")
@login_required
@manager_only
def manager():
    all_users = db.session.execute(db.select(Users)).scalars().all()    
    all_tasks = db.session.execute(db.select(Tasks)).scalars().all()
    stats = build_stats(all_tasks)

    team = []
    for user in all_users:
        team.append({"user": user, "stats": build_stats(user.tasks)})

    chart_status = status_chart(stats)
    chart_users=user_chart(team)
    return render_template("manager.html",
                           users=all_users,
                           tasks=all_tasks,
                           stats=stats,
                           today=date.today(),
                           team=team,
                           chart_status=chart_status,
                           chart_users=chart_users)

@app.route("/export")
@login_required
@manager_only
def export():
    all_tasks = db.session.execute(db.select(Tasks)).scalars().all()
    rows = []
    for task in all_tasks:
        rows.append({
            "Task": task.title,
            "User": task.user.name,
            "Email": task.user.email,
            "Status": task.status,
            "Priority": task.priority,
            "Due Date": task.due_date
        })
    df = pd.DataFrame(rows)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, download_name="team_pulse.xlsx", as_attachment=True)

@app.route("/api/tasks")
def api_tasks():
    api_key = request.headers.get("x-api-key")
    if not API_KEY or api_key != API_KEY:
            return jsonify(error="Not authorized"), 401
    
    status = request.args.get("status")
    user_id = request.args.get("user_id", type=int)
    priority = request.args.get("priority")

    query = db.select(Tasks)
    
    if status:
        query = query.where(Tasks.status == status)
    if user_id:
        query = query.where(Tasks.user_id == user_id)
    if priority:
        query = query.where(Tasks.priority == priority)

    tasks = db.session.execute(query).scalars().all()

    if not tasks:
        return jsonify(error="No tasks found"), 404

    return jsonify([task.to_dict() for task in tasks])

if __name__ == '__main__':
    app.run(debug=True)
