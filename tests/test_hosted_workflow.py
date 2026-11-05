from io import BytesIO
from pathlib import Path

from app import create_app
from config import ProductionConfig
from conftest import csrf_token
from extensions import db
from test_database import run_migration


def test_https_workspace_persists_imported_case(tmp_path, monkeypatch):
    class HostedConfig(ProductionConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'hosted.db').as_posix()}"

    monkeypatch.setenv("CYBERRISK_SECRET_KEY", "x" * 48)
    hostname = "https://hosted.example.test"

    def sign_in(app):
        client = app.test_client()
        page = client.get("/login", base_url=hostname)
        response = client.post("/login", base_url=hostname, headers={"Referer": hostname + "/login"}, data={
            "username": "operator", "password": "hosted-test-password",
            "csrf_token": csrf_token(page),
        })
        assert response.status_code == 302
        return client

    app = create_app(HostedConfig)
    run_migration(app, "upgrade")
    created = app.test_cli_runner().invoke(
        args=["create-user", "--username", "operator", "--role", "analyst"],
        input="hosted-test-password\nhosted-test-password\n",
    )
    assert created.exit_code == 0, created.output
    client = sign_in(app)
    path = "/alerts/import"
    token = csrf_token(client.get(path, base_url=hostname))
    raw = (Path(__file__).resolve().parents[1] / "examples" / "wazuh-alerts.jsonl").read_bytes()
    imported = client.post(path, base_url=hostname, headers={"Referer": hostname + path}, data={
        "csrf_token": token, "source": "hosted-lab", "upload": (BytesIO(raw), "alerts.jsonl"),
    })
    assert imported.status_code == 302
    path = "/alerts/1"
    converted = client.post(path + "/convert", base_url=hostname,
                            headers={"Referer": hostname + path}, data={
                                "csrf_token": csrf_token(client.get(path, base_url=hostname)),
                            })
    assert converted.status_code == 302
    report = client.get("/reports/incidents.pdf", base_url=hostname)
    assert report.status_code == 200 and report.data.startswith(b"%PDF")
    with app.app_context():
        db.engine.dispose()

    reloaded = create_app(HostedConfig)
    assert b"repeated SSH authentication failures" in sign_in(reloaded).get(
        converted.location, base_url=hostname,
    ).data
    with reloaded.app_context():
        db.engine.dispose()
