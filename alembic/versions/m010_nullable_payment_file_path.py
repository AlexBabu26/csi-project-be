"""allow null payment proof file_path for backfilled records

Revision ID: m010
Revises: m009
"""

revision = 'm010'
down_revision = 'm009'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.alter_column(
        'unit_registration_payment',
        'file_path',
        existing_type=sa.String(500),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'unit_registration_payment',
        'file_path',
        existing_type=sa.String(500),
        nullable=False,
    )
