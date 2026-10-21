"""Game provider ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.roi import RoiSet


class GameProvider(Base):
    """A provider that supplies games to the automation system."""

    __tablename__ = "game_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    roi_sets: Mapped[list["RoiSet"]] = relationship(
        back_populates="game_provider",
        cascade="all, delete-orphan",
        order_by="RoiSet.id",
        lazy="selectin",
    )
