from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db
from models.timestamps import utc_now


class Asset(db.Model):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120))
    criticality: Mapped[str] = mapped_column(String(8))
    environment: Mapped[str] = mapped_column(String(12))
    internet_exposed: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
