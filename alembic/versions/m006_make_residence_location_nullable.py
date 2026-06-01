"""make residence_location nullable and clear existing values

Revision ID: m006
Revises: m005
"""

revision = 'm006'
down_revision = 'm005'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.alter_column(
        'unit_members',
        'residence_location',
        existing_type=sa.Enum(
            'WITHIN_KERALA',
            'OUTSIDE_KERALA',
            'OUTSIDE_INDIA',
            name='residencelocation',
        ),
        nullable=True,
        server_default=None,
    )
    op.execute("UPDATE unit_members SET residence_location = NULL")


def downgrade() -> None:
    op.execute("UPDATE unit_members SET residence_location = 'WITHIN_KERALA' WHERE residence_location IS NULL")
    op.alter_column(
        'unit_members',
        'residence_location',
        existing_type=sa.Enum(
            'WITHIN_KERALA',
            'OUTSIDE_KERALA',
            'OUTSIDE_INDIA',
            name='residencelocation',
        ),
        nullable=False,
        server_default='WITHIN_KERALA',
    )
