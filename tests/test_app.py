import pytest

from app import create_app, db, Task


@pytest.fixture
def client(tmp_path):
    database_path = tmp_path / "test.db"

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
    })

    with app.app_context():
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Moje zadania".encode() in response.data


def test_add_task(client):
    response = client.post(
        "/add",
        data={
            "title": "Nauczyć się Dockera",
            "description": "Przygotować projekt na zaliczenie",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Nauczyć się Dockera".encode() in response.data

    with client.application.app_context():
        task = db.session.execute(
            db.select(Task).where(Task.title == "Nauczyć się Dockera")
        ).scalar_one()

        assert task.description == "Przygotować projekt na zaliczenie"
        assert task.completed is False


def test_complete_task(client):
    with client.application.app_context():
        task = Task(title="Test wykonania")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = client.post(
        f"/complete/{task_id}",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.application.app_context():
        task = db.session.get(Task, task_id)
        assert task.completed is True


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"

