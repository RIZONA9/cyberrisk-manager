from sqlalchemy import func, select

from app import create_app
from config import TestingConfig
from conftest import csrf_token
from extensions import db
from models import Incident, ResponseAction, RiskAssessment, Simulation, SimulationEvent, User


def test_seed_migrates_is_idempotent_and_preserves_password(tmp_path):
    class SeedConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'demo-test.db').as_posix()}"

    app = create_app(SeedConfig)
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0, first.output
    assert "Added 3 sample incidents and 4 simulations" in first.output
    client = app.test_client()
    token = csrf_token(client.get("/login"))
    assert client.post("/login", data={
        "csrf_token": token, "username": "admin", "password": "Admin@12345",
    }).location == "/"

    models = (User, Incident, RiskAssessment, ResponseAction, Simulation, SimulationEvent)
    with app.app_context():
        counts = [db.session.scalar(select(func.count()).select_from(model)) for model in models]
        assert counts == [1, 7, 14, 27, 4, 36]
        user = db.session.scalars(select(User)).one()
        assert user.password_hash != "Admin@12345"
        user.set_password("replacement-password")
        db.session.commit()

    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0, second.output
    assert "Added 0 sample incidents and 0 simulations" in second.output
    with app.app_context():
        assert [db.session.scalar(select(func.count()).select_from(model)) for model in models] == counts
        assert db.session.scalars(select(User)).one().check_password("replacement-password")
        db.engine.dispose()
