import importlib
import sys


def test_wsgi_entry_sets_host_and_uses_https_cookies(monkeypatch):
    monkeypatch.setenv("CYBERRISK_SECRET_KEY", "x" * 48)
    monkeypatch.setenv("CYBERRISK_HOSTNAME", "cyberrisk.example.test")
    monkeypatch.delitem(sys.modules, "wsgi", raising=False)
    wsgi = importlib.import_module("wsgi")
    app = wsgi.application
    assert app.config["SESSION_COOKIE_SECURE"]
    assert app.test_client().get("/login", base_url="https://other.example.test").status_code == 400
    assert app.test_client().get("/login", base_url="https://cyberrisk.example.test").status_code == 200
