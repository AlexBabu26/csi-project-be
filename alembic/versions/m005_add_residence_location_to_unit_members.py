"""add residence_location to unit_members

Revision ID: m005
Revises: m004
"""

revision = 'm005'
down_revision = 'm004'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    residence_location_enum = sa.Enum(
        'WITHIN_KERALA',
        'OUTSIDE_KERALA',
        'OUTSIDE_INDIA',
        name='residencelocation',
    )
    residence_location_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'unit_members',
        sa.Column(
            'residence_location',
            residence_location_enum,
            nullable=False,
            server_default='WITHIN_KERALA',
        ),
    )


def downgrade() -> None:
    op.drop_column('unit_members', 'residence_location')
    sa.Enum(name='residencelocation').drop(op.get_bind(), checkfirst=True)
