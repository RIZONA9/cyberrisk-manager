import re

import pytest
from flask import jsonify, render_template_string, request

from app import create_app
from config import TestingConfig
from forms.auth_forms import LoginForm
from forms.risk_forms import InitialRiskForm


@pytest.fixture
def client():
    app = create_app(TestingConfig)

    @app.route("/form-test", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def form_test():
        form = LoginForm()
        if request.method == "GET":
            return render_template_string("{{ form.hidden_tag() }}", form=form)
        return jsonify(accepted=form.validate())

    return app.test_client()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_missing_csrf_token_is_rejected(client, method):
    assert client.open("/form-test", method=method).status_code == 400


def test_invalid_csrf_token_is_rejected(client):
    client.get("/form-test")
    assert client.post("/form-test", data={"csrf_token": "invalid"}).status_code == 400


@pytest.mark.parametrize("via_header", [False, True])
def test_valid_csrf_token_is_accepted(client, via_header):
    html = client.get("/form-test").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)[1]
    data = {"username": "analyst", "password": "example-password"}
    headers = {}
    if via_header:
        headers["X-CSRFToken"] = token
    else:
        data["csrf_token"] = token
    response = client.post("/form-test", data=data, headers=headers)
    assert response.status_code == 200
    assert response.json == {"accepted": True}


@pytest.mark.parametrize("likelihood", ["0", "6", "2.5", "abc"])
def test_risk_form_rejects_invalid_likelihood(likelihood):
    app = create_app(TestingConfig)
    with app.test_request_context(method="POST", data={"likelihood": likelihood, "impact": "3"}):
        form = InitialRiskForm()
        assert not form.validate()
        assert form.likelihood.errors
