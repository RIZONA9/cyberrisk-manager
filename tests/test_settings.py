import pytest

from app import create_app
from conftest import csrf_token


def sign_in(client, password):
    token = csrf_token(client.get("/login"))
    return client.post("/login", data={
        "username": "admin", "password": password, "csrf_token": token,
    })


def test_password_change_rejects_invalid_current_password_and_ends_sessions(app, signed_in):
    other_client = app.test_client()
    assert sign_in(other_client, "test-password").location == "/"
    path = "/settings/"
    token = csrf_token(signed_in.get(path))
    data = {
        "csrf_token": token, "new_password": "new-local-password",
        "confirm_password": "new-local-password",
    }
    assert b"current password is incorrect" in signed_in.post(
        path, data={**data, "current_password": "wrong"},
    ).data
    assert signed_in.post(path, data={**data, "current_password": "test-password"}).location == "/login"
    assert other_client.get("/").location.startswith("/login")
    assert b"Invalid username or password" in sign_in(signed_in, "test-password").data
    assert sign_in(signed_in, "new-local-password").location == "/"


def test_production_requires_secret_and_disables_demo(monkeypatch):
    monkeypatch.setenv("CYBERRISK_ENV", "production")
    monkeypatch.delenv("CYBERRISK_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CYBERRISK_SECRET_KEY"):
        create_app()
    monkeypatch.setenv("CYBERRISK_SECRET_KEY", "x" * 48)
    app = create_app()
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code == 1 and "only for local development" in result.output
    response = app.test_client().get("/login", base_url="https://localhost")
    cookie = response.headers["Set-Cookie"]
    assert all(attribute in cookie for attribute in ("Secure", "HttpOnly", "SameSite=Lax"))
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
