"""Game ORM model."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.game_provider import GameProvider


class Game(Base):
    """A game offered by a single game provider."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    number_of_spins: Mapped[int]
    url: Mapped[str] = mapped_column(String(2048))
    game_provider_id: Mapped[int] = mapped_column(
        ForeignKey("game_providers.id")
    )

    game_provider: Mapped[GameProvider] = relationship()
