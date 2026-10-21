"""Game provider ORM model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GameProvider(Base):
    """A provider that supplies games to the automation system."""

    __tablename__ = "game_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
