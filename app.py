from secrets import compare_digest

from flask import Flask, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import Conflict

from config import configured_profile
from extensions import csrf, db, init_database, login_manager
from models import User
from modules.backup import backup_database
from modules.demo_data import seed_demo
from routes import alerts, assets, auth, dashboard, exercises, governance, incidents, reports, responses, risk_register, risks, settings, simulations, vulnerabilities


@login_manager.user_loader
def load_user(session_id):
    user_id, separator, fingerprint = session_id.partition(":")
    if not separator or not fingerprint.isascii() or not user_id.isascii() or not user_id.isdecimal():
        return None
    if len(user_id) > 19 or int(user_id) > 2**63 - 1:
        return None
    user = db.session.get(User, int(user_id))
    return user if user and compare_digest(user.get_id(), session_id) else None


def create_app(config=None):
    if config is None:
        config = configured_profile()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config)
    app.config["SECRET_KEY"] = config.secret_key()
    init_database(app)
    csrf.init_app(app)
    login_manager.init_app(app, add_context_processor=False)
    app.jinja_env.globals["current_user"] = current_user
    app.register_blueprint(auth.bp)
    app.register_blueprint(assets.bp)
    app.register_blueprint(alerts.bp)
    app.register_blueprint(governance.bp)
    app.register_blueprint(vulnerabilities.bp)
    app.register_blueprint(exercises.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(incidents.bp)
    app.register_blueprint(risks.bp)
    app.register_blueprint(risk_register.bp)
    app.register_blueprint(responses.bp)
    app.register_blueprint(simulations.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(settings.bp)
    app.cli.add_command(simulations.recover_simulations)
    app.cli.add_command(seed_demo)
    app.cli.add_command(settings.create_user)
    app.cli.add_command(backup_database)

    def error_page(code, title, detail):
        return render_template("error.html", code=code, title=title, detail=detail,
                               hide_session=code == 500), code

    @app.errorhandler(CSRFError)
    def handle_csrf_error(_error):
        return error_page(400, "Security token rejected",
                          "Reload the page to get a fresh token, then try again.")

    @app.errorhandler(404)
    def handle_not_found(_error):
        return error_page(404, "Page not found", "The requested record or page is unavailable.")

    @app.errorhandler(403)
    def handle_forbidden(_error):
        return error_page(403, "Access restricted", "Your account role does not allow this action.")

    @app.errorhandler(Conflict)
    def handle_conflict(error):
        return error_page(409, "Request conflicts with the record", error.description)

    @app.errorhandler(413)
    def handle_large_request(_error):
        return error_page(413, "Request too large", "Shorten the submitted content and try again.")

    @app.errorhandler(500)
    def handle_server_error(_error):
        db.session.rollback()
        return error_page(500, "Request could not be completed", "Try again from the workspace.")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        if request.endpoint != "static":
            response.cache_control.no_store = True
        return response

    return app
