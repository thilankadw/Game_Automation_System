"""OCR-extracted spin readings."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SpinReading(Base):
    """Balance, bet, and win values read from one stored screenshot frame."""

    __tablename__ = "spin_readings"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "session_id",
            "spin_number",
            name="uq_spin_readings_game_session_spin",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    spin_number: Mapped[int] = mapped_column()
    balance: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    bet: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    win: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    balance_text: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    bet_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    win_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    screenshot_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
