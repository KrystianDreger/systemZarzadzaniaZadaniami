import csv
import io
import os
from datetime import date

from flask import (
    Flask, abort, make_response, redirect, render_template, request, url_for
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()

PRIORITIES = {"low": "Niski", "medium": "Średni", "high": "Wysoki"}


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    priority = db.Column(db.String(10), nullable=False, default="medium")
    due_date = db.Column(db.Date, nullable=True)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://taskuser:taskpassword@db:3306/taskdb",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if test_config:
        app.config.update(test_config)
    db.init_app(app)

    @app.route("/")
    def index():
        search = request.args.get("q", "").strip()
        status = request.args.get("status", "all")
        priority = request.args.get("priority", "all")
        today = date.today()

        stmt = db.select(Task)
        if search:
            stmt = stmt.where(
                db.or_(
                    Task.title.ilike(f"%{search}%"),
                    Task.description.ilike(f"%{search}%"),
                )
            )
        if status == "open":
            stmt = stmt.where(Task.completed.is_(False))
        elif status == "done":
            stmt = stmt.where(Task.completed.is_(True))
        if priority in PRIORITIES:
            stmt = stmt.where(Task.priority == priority)

        tasks = db.session.execute(
            stmt.order_by(Task.completed.asc(), Task.due_date.asc(), Task.id.desc())
        ).scalars().all()

        all_tasks = db.session.execute(db.select(Task)).scalars().all()
        total = len(all_tasks)
        completed_count = sum(task.completed for task in all_tasks)
        overdue_count = sum(
            not task.completed and task.due_date is not None and task.due_date < today
            for task in all_tasks
        )
        stats = {
            "total": total,
            "completed": completed_count,
            "open": total - completed_count,
            "overdue": overdue_count,
            "progress": round(completed_count / total * 100) if total else 0,
        }
        return render_template(
            "index.html",
            tasks=tasks,
            stats=stats,
            search=search,
            status=status,
            priority=priority,
            today=today,
            priorities=PRIORITIES,
        )

    @app.route("/add", methods=["POST"])
    def add_task():
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        due_date_raw = request.form.get("due_date", "").strip()

        if not title or len(title) > 150:
            return redirect(url_for("index"))
        if priority not in PRIORITIES:
            priority = "medium"
        try:
            due_date = date.fromisoformat(due_date_raw) if due_date_raw else None
        except ValueError:
            due_date = None

        db.session.add(Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
        ))
        db.session.commit()
        return redirect(url_for("index"))

    @app.route("/complete/<int:task_id>", methods=["POST"])
    def complete_task(task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            abort(404)
        task.completed = not task.completed
        db.session.commit()
        return redirect(request.referrer or url_for("index"))

    @app.route("/edit/<int:task_id>", methods=["GET", "POST"])
    def edit_task(task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            abort(404)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title or len(title) > 150:
                return render_template(
                    "edit.html", task=task, priorities=PRIORITIES,
                    error="Nazwa jest wymagana i może mieć maksymalnie 150 znaków."
                ), 400
            priority = request.form.get("priority", "medium")
            if priority not in PRIORITIES:
                priority = "medium"
            due_date_raw = request.form.get("due_date", "").strip()
            try:
                due_date = date.fromisoformat(due_date_raw) if due_date_raw else None
            except ValueError:
                due_date = None
            task.title = title
            task.description = request.form.get("description", "").strip()
            task.priority = priority
            task.due_date = due_date
            db.session.commit()
            return redirect(url_for("index"))
        return render_template("edit.html", task=task, priorities=PRIORITIES, error=None)

    @app.route("/delete/<int:task_id>", methods=["POST"])
    def delete_task(task_id):
        task = db.session.get(Task, task_id)
        if task is None:
            abort(404)
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for("index"))

    @app.route("/export.csv")
    def export_csv():
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["ID", "Nazwa", "Opis", "Status", "Priorytet", "Termin", "Utworzono"])
        tasks = db.session.execute(
            db.select(Task).order_by(Task.id.asc())
        ).scalars().all()
        for task in tasks:
            writer.writerow([
                task.id, task.title, task.description,
                "Wykonane" if task.completed else "Do zrobienia",
                PRIORITIES.get(task.priority, "Średni"),
                task.due_date.isoformat() if task.due_date else "",
                task.created_at.isoformat(sep=" ") if task.created_at else "",
            ])
        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=zadania.csv"
        return response

    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}, 200
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "error", "database": "unavailable"}, 503

    @app.cli.command("init-db")
    def init_db():
        """Utwórz brakujące tabele bazy danych."""
        db.create_all()
        print("Baza danych została zainicjalizowana.")

    @app.cli.command("migrate-task-fields")
    def migrate_task_fields():
        """Dodaj nowe kolumny do istniejącej tabeli tasks bez kasowania danych."""
        db.create_all()
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("task")}
        # Nazwa tabeli w SQLAlchemy wynika z nazwy klasy: task.
        if "priority" not in columns:
            db.session.execute(text(
                "ALTER TABLE task ADD COLUMN priority VARCHAR(10) NOT NULL DEFAULT 'medium'"
            ))
        if "due_date" not in columns:
            # MySQL i SQLite obsługują typ DATE.
            db.session.execute(text("ALTER TABLE task ADD COLUMN due_date DATE NULL"))
        db.session.commit()
        print("Migracja zakończona. Istniejące zadania zachowano.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
