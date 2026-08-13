"""link posted transactions back to their recurring schedule

Revision ID: d4a6b7c8e9f0
Revises: f7b2a41c6e03
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a6b7c8e9f0'
down_revision: Union[str, Sequence[str], None] = 'f7b2a41c6e03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'transactions',
        sa.Column('recurring_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_transactions_recurring_id'),
        'transactions',
        ['recurring_id'],
        unique=False,
    )
    op.create_foreign_key(
        op.f('fk_transactions_recurring_id_recurring_transactions'),
        'transactions',
        'recurring_transactions',
        ['recurring_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f('fk_transactions_recurring_id_recurring_transactions'),
        'transactions',
        type_='foreignkey',
    )
    op.drop_index(op.f('ix_transactions_recurring_id'), table_name='transactions')
    op.drop_column('transactions', 'recurring_id')