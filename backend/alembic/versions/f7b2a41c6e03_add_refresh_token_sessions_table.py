"""add refresh_token_sessions table

Revision ID: f7b2a41c6e03
Revises: c1a5e3b9f4d2
Create Date: 2026-08-12 22:45:00.000000

Refresh-token sessions are stored by the SHA-256 hash of the token's ``jti``
so rotation and logout can revoke a specific issued session (prevents replay
of a stolen previous-generation refresh token).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2a41c6e03'
down_revision: Union[str, Sequence[str], None] = 'c1a5e3b9f4d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('refresh_token_sessions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('jti_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_token_sessions_jti_hash'), 'refresh_token_sessions', ['jti_hash'], unique=True)
    op.create_index(op.f('ix_refresh_token_sessions_user_id'), 'refresh_token_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_refresh_token_sessions_user_id'), table_name='refresh_token_sessions')
    op.drop_index(op.f('ix_refresh_token_sessions_jti_hash'), table_name='refresh_token_sessions')
    op.drop_table('refresh_token_sessions')