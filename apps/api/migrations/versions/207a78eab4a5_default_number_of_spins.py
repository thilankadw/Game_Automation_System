"""default number of spins

Revision ID: 207a78eab4a5
Revises: efc87a63b4fb
Create Date: 2026-10-21 16:13:28.734083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '207a78eab4a5'
down_revision: Union[str, Sequence[str], None] = 'efc87a63b4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a default of 1000 spins to the games table."""
    with op.batch_alter_table("games") as batch_op:
        batch_op.alter_column(
            "number_of_spins",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=sa.text("1000"),
        )


def downgrade() -> None:
    """Remove the default number of spins."""
    with op.batch_alter_table("games") as batch_op:
        batch_op.alter_column(
            "number_of_spins",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=None,
        )
