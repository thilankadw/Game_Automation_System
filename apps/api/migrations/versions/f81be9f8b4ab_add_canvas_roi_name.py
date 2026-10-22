"""add canvas roi name

Revision ID: f81be9f8b4ab
Revises: 802179067d7c
Create Date: 2026-10-22 09:21:49.759966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f81be9f8b4ab'
down_revision: Union[str, Sequence[str], None] = '802179067d7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_CHECK = "name IN ('canvas', 'spin_button', 'balance', 'bet', 'win')"
_OLD_CHECK = "name IN ('spin_button', 'balance', 'bet', 'win')"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('rois', schema=None) as batch_op:
        batch_op.drop_constraint('ck_rois_name', type_='check')
        batch_op.create_check_constraint('ck_rois_name', _NEW_CHECK)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('rois', schema=None) as batch_op:
        batch_op.drop_constraint('ck_rois_name', type_='check')
        batch_op.create_check_constraint('ck_rois_name', _OLD_CHECK)
