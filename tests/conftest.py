import re

import pytest

from app import create_app
from config import TestingConfig
from extensions import db
from models import User


@pytest.fixture
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        user = User(username="admin", role="admin")
        user.set_password("test-password")
        db.session.add(user)
        db.session.commit()
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(response):
    return re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)[1].decode()


@pytest.fixture
def signed_in(client):
    token = csrf_token(client.get("/login"))
    response = client.post("/login", data={
        "csrf_token": token, "username": "admin", "password": "test-password",
    })
    assert response.location == "/"
    return client
