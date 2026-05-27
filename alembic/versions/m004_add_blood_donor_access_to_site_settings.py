"""add blood_donor_district_access and blood_donor_unit_access to site_settings

Revision ID: m004
Revises: m003
Branch Labels: None
Depends On: None
"""

revision = 'm004'
down_revision = 'm003'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'site_settings',
        sa.Column('blood_donor_district_access', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'site_settings',
        sa.Column('blood_donor_unit_access', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('site_settings', 'blood_donor_unit_access')
    op.drop_column('site_settings', 'blood_donor_district_access')
