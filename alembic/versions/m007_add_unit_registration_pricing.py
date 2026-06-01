"""add unit registration pricing to site_settings

Revision ID: m007
Revises: m006
"""

revision = 'm007'
down_revision = 'm006'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'site_settings',
        sa.Column('unit_registration_fee', sa.Integer(), nullable=False, server_default='100'),
    )
    op.add_column(
        'site_settings',
        sa.Column('unit_member_fee', sa.Integer(), nullable=False, server_default='10'),
    )


def downgrade() -> None:
    op.drop_column('site_settings', 'unit_member_fee')
    op.drop_column('site_settings', 'unit_registration_fee')
