"""add spin readings

Revision ID: 25f5b7afc9af
Revises: 02f5f6cb3a81
Create Date: 2026-10-22 17:21:00.506333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25f5b7afc9af'
down_revision: Union[str, Sequence[str], None] = '02f5f6cb3a81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'spin_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('spin_number', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('bet', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('win', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('balance_text', sa.String(length=255), nullable=True),
        sa.Column('bet_text', sa.String(length=255), nullable=True),
        sa.Column('win_text', sa.String(length=255), nullable=True),
        sa.Column('screenshot_path', sa.String(length=1024), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['game_id'],
            ['games.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'game_id',
            'session_id',
            'spin_number',
            name='uq_spin_readings_game_session_spin',
        ),
    )
    with op.batch_alter_table('spin_readings', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_spin_readings_game_id'),
            ['game_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_spin_readings_session_id'),
            ['session_id'],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('spin_readings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_spin_readings_session_id'))
        batch_op.drop_index(batch_op.f('ix_spin_readings_game_id'))

    op.drop_table('spin_readings')
