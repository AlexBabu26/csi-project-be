"""add balance_amount to unit_registration_payment

Revision ID: m017
Revises: m016
"""

revision = 'm017'
down_revision = 'm016'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'unit_registration_payment',
        sa.Column('balance_amount', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('unit_registration_payment', 'balance_amount')
