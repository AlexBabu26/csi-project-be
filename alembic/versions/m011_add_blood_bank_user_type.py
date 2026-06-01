"""add BLOOD_BANK user type

Revision ID: m011
Revises: m010
"""

revision = 'm011'
down_revision = 'm010'
branch_labels = None
depends_on = None

from alembic import op


def upgrade() -> None:
    op.execute("ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'BLOOD_BANK'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely.
    pass
