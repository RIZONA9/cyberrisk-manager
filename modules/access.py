from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from extensions import db
from models.governance import AuditEvent


def roles_required(*roles):
    def decorate(view):
        @login_required
        @wraps(view)
        def protected(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return protected
    return decorate


editor_required = roles_required("admin", "analyst")


def audit(action, target, *, before=None, after=None, reason=None):
    db.session.add(AuditEvent(
        actor=current_user.username, action=action, target=target,
        before=before, after=after, reason=reason,
    ))
