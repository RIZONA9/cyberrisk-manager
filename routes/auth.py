from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from extensions import db
from forms.auth_forms import LoginForm
from models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(User.username == form.username.data))
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("dashboard.index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
