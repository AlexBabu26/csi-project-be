"""add_refresh_token_table_clean

Revision ID: 71c337eb431c
Revises: 092715b26998
Create Date: 2025-12-08 02:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71c337eb431c'
down_revision: Union[str, None] = '092715b26998'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create refresh_token table
    op.create_table('refresh_token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['custom_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refresh_token_id', 'refresh_token', ['id'], unique=False)
    op.create_index('ix_refresh_token_token', 'refresh_token', ['token'], unique=True)
    op.create_index('ix_refresh_token_user_id', 'refresh_token', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop refresh_token table
    op.drop_index('ix_refresh_token_user_id', table_name='refresh_token')
    op.drop_index('ix_refresh_token_token', table_name='refresh_token')
    op.drop_index('ix_refresh_token_id', table_name='refresh_token')
    op.drop_table('refresh_token')
