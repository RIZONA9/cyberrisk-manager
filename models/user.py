from datetime import datetime
from hashlib import sha256

from flask_login import UserMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models.timestamps import utc_now


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(8), default="analyst", server_default="analyst")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        # Replacing the stored password hash invalidates older signed sessions.
        fingerprint = sha256(self.password_hash.encode()).hexdigest()
        return f"{self.id}:{fingerprint}"
