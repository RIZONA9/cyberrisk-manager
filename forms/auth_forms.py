from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import EqualTo, InputRequired, Length

from forms import text_field


class LoginForm(FlaskForm):
    username = text_field("Username", 80, render_kw={"autocomplete": "username"})
    password = PasswordField(
        "Password", validators=[InputRequired(), Length(max=256)],
        render_kw={"autocomplete": "current-password"},
    )


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField(
        "Current password", validators=[InputRequired(), Length(max=256)]
    )
    new_password = PasswordField(
        "New password", validators=[InputRequired(), Length(min=12, max=256)]
    )
    confirm_password = PasswordField(
        "Confirm new password", validators=[InputRequired(), EqualTo("new_password"), Length(max=256)]
    )
