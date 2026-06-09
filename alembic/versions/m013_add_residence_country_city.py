"""add residence_country and residence_city to unit_members

Revision ID: m013_add_residence_country_city
Revises: m012_add_archived_member_concern_request
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = 'm013'
down_revision = 'm012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('unit_members', sa.Column('residence_country', sa.String(length=100), nullable=True))
    op.add_column('unit_members', sa.Column('residence_city', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('unit_members', 'residence_city')
    op.drop_column('unit_members', 'residence_country')
