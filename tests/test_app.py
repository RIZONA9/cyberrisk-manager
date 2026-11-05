from app import create_app
from config import DevelopmentConfig, TestingConfig


def test_home_page_responds():
    app = create_app(TestingConfig)

    response = app.test_client().get("/login")

    assert response.status_code == 200
    assert "CyberRisk Manager" in response.get_data(as_text=True)
    assert app.testing
    assert not app.debug


def test_development_uses_environment_secret(monkeypatch):
    monkeypatch.setenv("CYBERRISK_SECRET_KEY", "test-environment-value")

    app = create_app(DevelopmentConfig)

    assert app.secret_key == "test-environment-value"
    assert not app.testing
    assert app.config["SESSION_COOKIE_HTTPONLY"]
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert not app.config["SESSION_COOKIE_SECURE"]
