"""add member_min_dob and member_max_dob to site_settings

Revision ID: m002
Revises: ym001
Branch Labels: None
Depends On: None
"""

revision = 'm002'
down_revision = 'ym001'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'site_settings',
        sa.Column(
            'member_min_dob',
            sa.Date(),
            nullable=True,
            server_default='1990-01-01',
        ),
    )
    op.add_column(
        'site_settings',
        sa.Column(
            'member_max_dob',
            sa.Date(),
            nullable=True,
            server_default='2011-12-31',
        ),
    )


def downgrade() -> None:
    op.drop_column('site_settings', 'member_max_dob')
    op.drop_column('site_settings', 'member_min_dob')
