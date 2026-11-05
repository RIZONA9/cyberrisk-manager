import click
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask.cli import with_appcontext
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms.auth_forms import PasswordChangeForm
from models import User

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("The current password is incorrect.")
        elif form.current_password.data == form.new_password.data:
            form.new_password.errors.append("Choose a password different from the current password.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            logout_user()
            flash("Password updated. Sign in with your new password.", "success")
            return redirect(url_for("auth.login"))

    return render_template(
        "settings.html", form=form, allow_demo=current_app.config["ALLOW_DEMO_DATA"],
        secure_cookie=current_app.config["SESSION_COOKIE_SECURE"],
    )


@click.command("create-user")
@click.option("--username", prompt=True)
@click.option("--role", type=click.Choice(("admin", "analyst", "reviewer")), default="analyst", show_default=True)
@with_appcontext
def create_user(username, role):
    """Create an account with a password entered at a private prompt."""
    username = username.strip()
    if not 1 <= len(username) <= 80:
        raise click.ClickException("Username must contain 1 to 80 characters.")
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    if not 12 <= len(password) <= 256:
        raise click.ClickException("Password must contain 12 to 256 characters.")
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise click.ClickException("That username already exists.") from error
    click.echo(f"Created account {username}.")
