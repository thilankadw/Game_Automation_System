"""ROI set and ROI ORM models."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.game_provider import GameProvider


class RoiName(StrEnum):
    """UI elements that can be marked on a provider or game screen."""

    SPIN_BUTTON = "spin_button"
    BALANCE = "balance"
    BET = "bet"
    WIN = "win"


class RoiSet(Base):
    """A named collection of ROIs owned by a game provider.

    Providers keep multiple sets so the same game provider can be automated
    with different layouts. Games reference a set instead of copying ROIs.
    """

    __tablename__ = "roi_sets"
    __table_args__ = (
        UniqueConstraint(
            "game_provider_id",
            "name",
            name="uq_roi_sets_provider_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    game_provider_id: Mapped[int] = mapped_column(
        ForeignKey("game_providers.id")
    )

    game_provider: Mapped["GameProvider"] = relationship(
        back_populates="roi_sets"
    )
    rois: Mapped[list["Roi"]] = relationship(
        back_populates="roi_set",
        cascade="all, delete-orphan",
        order_by="Roi.id",
        lazy="selectin",
    )


class Roi(Base):
    """A rectangular region for a single UI element in a ROI set."""

    __tablename__ = "rois"
    __table_args__ = (
        CheckConstraint(
            "name IN ('spin_button', 'balance', 'bet', 'win')",
            name="ck_rois_name",
        ),
        UniqueConstraint("roi_set_id", "name", name="uq_rois_set_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    roi_set_id: Mapped[int] = mapped_column(ForeignKey("roi_sets.id"))
    name: Mapped[str] = mapped_column(String(32))
    x: Mapped[int] = mapped_column()
    y: Mapped[int] = mapped_column()
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()

    roi_set: Mapped[RoiSet] = relationship(back_populates="rois")
