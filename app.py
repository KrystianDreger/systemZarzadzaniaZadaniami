import os

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    completed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


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

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        tasks = db.session.execute(
            db.select(Task).order_by(Task.id.desc())
        ).scalars().all()

        return render_template("index.html", tasks=tasks)

    @app.route("/add", methods=["POST"])
    def add_task():
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            return redirect(url_for("index"))

        task = Task(title=title, description=description)
        db.session.add(task)
        db.session.commit()

        return redirect(url_for("index"))

    @app.route("/complete/<int:task_id>", methods=["POST"])
    def complete_task(task_id):
        task = db.session.get(Task, task_id)

        if task is not None:
            task.completed = not task.completed
            db.session.commit()

        return redirect(url_for("index"))

    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}, 200
        except SQLAlchemyError:
            db.session.rollback()
            return {"status": "error", "database": "unavailable"}, 503

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10101)

