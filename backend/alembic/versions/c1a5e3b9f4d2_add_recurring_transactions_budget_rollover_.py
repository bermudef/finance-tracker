"""add recurring transactions, budget rollover, email verification

Revision ID: c1a5e3b9f4d2
Revises: 088d0694d744
Create Date: 2026-08-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a5e3b9f4d2'
down_revision: Union[str, Sequence[str], None] = '088d0694d744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('budgets', sa.Column('rollover', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('verification_token', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_users_verification_token'), 'users', ['verification_token'], unique=False)
    op.create_table('recurring_transactions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('frequency', sa.String(length=20), nullable=False),
    sa.Column('next_date', sa.Date(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_transactions_account_id'), 'recurring_transactions', ['account_id'], unique=False)
    op.create_index(op.f('ix_recurring_transactions_category_id'), 'recurring_transactions', ['category_id'], unique=False)
    op.create_index(op.f('ix_recurring_transactions_next_date'), 'recurring_transactions', ['next_date'], unique=False)
    op.create_index(op.f('ix_recurring_transactions_user_id'), 'recurring_transactions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recurring_transactions_user_id'), table_name='recurring_transactions')
    op.drop_index(op.f('ix_recurring_transactions_next_date'), table_name='recurring_transactions')
    op.drop_index(op.f('ix_recurring_transactions_category_id'), table_name='recurring_transactions')
    op.drop_index(op.f('ix_recurring_transactions_account_id'), table_name='recurring_transactions')
    op.drop_table('recurring_transactions')
    op.drop_index(op.f('ix_users_verification_token'), table_name='users')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('budgets', 'rollover')
