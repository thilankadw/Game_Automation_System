"""Game ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.game_provider import GameProvider

if TYPE_CHECKING:
    from app.models.roi import RoiSet


class Game(Base):
    """A game offered by a single game provider."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    number_of_spins: Mapped[int] = mapped_column(
        default=1000, server_default="1000"
    )
    url: Mapped[str] = mapped_column(String(2048))
    game_provider_id: Mapped[int] = mapped_column(
        ForeignKey("game_providers.id")
    )
    roi_set_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "roi_sets.id",
            ondelete="SET NULL",
            name="fk_games_roi_set_id_roi_sets",
        ),
        nullable=True,
    )

    game_provider: Mapped[GameProvider] = relationship()
    roi_set: Mapped["RoiSet | None"] = relationship(lazy="selectin")
