"""add_is_active_to_events

Revision ID: d5a945c7bfca
Revises: 021cf2b91a60
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5a945c7bfca'
down_revision = '021cf2b91a60'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_active column to individual_event table with default True
    op.add_column('individual_event',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )
    
    # Add is_active column to group_event table with default True
    op.add_column('group_event',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade() -> None:
    # Drop is_active column from group_event
    op.drop_column('group_event', 'is_active')
    
    # Drop is_active column from individual_event
    op.drop_column('individual_event', 'is_active')
