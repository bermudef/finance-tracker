"""add auto_pay to recurring transactions

Revision ID: e2b7f6a91c4d
Revises: d4a6b7c8e9f0
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2b7f6a91c4d'
down_revision: Union[str, Sequence[str], None] = 'd4a6b7c8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'recurring_transactions',
        sa.Column('auto_pay', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('recurring_transactions', 'auto_pay')
