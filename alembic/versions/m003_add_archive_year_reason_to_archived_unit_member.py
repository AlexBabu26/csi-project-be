"""add archive_year and archive_reason to archived_unit_member

Revision ID: m003
Revises: m002
Branch Labels: None
Depends On: None
"""

revision = 'm003'
down_revision = 'm002'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'archived_unit_member',
        sa.Column('archive_year', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'archived_unit_member',
        sa.Column('archive_reason', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('archived_unit_member', 'archive_reason')
    op.drop_column('archived_unit_member', 'archive_year')
