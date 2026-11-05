from sqlalchemy import select

from conftest import csrf_token
from extensions import db
from models import User


def test_operator_account_created_via_cli(app):
    result = app.test_cli_runner().invoke(
        args=["create-user", "--username", "operator"],
        input="strong-operator-password\nstrong-operator-password\n",
    )
    assert result.exit_code == 0, result.output
    assert "strong-operator-password" not in result.output
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "operator"))
        assert user.check_password("strong-operator-password")


def test_error_page_is_safe_and_has_security_headers(signed_in):
    response = signed_in.post("/incidents/new", data={"title": "<script>alert(1)</script>"})
    assert response.status_code == 400
    assert b"Security token rejected" in response.data
    assert b"<script>alert(1)</script>" not in response.data
    assert "no-store" in response.headers["Cache-Control"]

    page = signed_in.get("/settings/")
    oversized = signed_in.post("/settings/", data={
        "csrf_token": csrf_token(page), "current_password": "x" * (257 * 1024),
    })
    assert oversized.status_code == 413
