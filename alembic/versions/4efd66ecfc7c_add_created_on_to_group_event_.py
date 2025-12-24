"""add_created_on_to_group_event_participation

Revision ID: 4efd66ecfc7c
Revises: d5a945c7bfca
Create Date: 2025-12-24

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '4efd66ecfc7c'
down_revision = 'd5a945c7bfca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add created_on column to group_event_participation table
    # First add as nullable, then set default values for existing rows, then make non-nullable
    op.add_column('group_event_participation', sa.Column('created_on', sa.DateTime(), nullable=True))
    
    # Update existing rows with current timestamp
    op.execute("UPDATE group_event_participation SET created_on = NOW() WHERE created_on IS NULL")
    
    # Make the column non-nullable
    op.alter_column('group_event_participation', 'created_on', nullable=False)


def downgrade() -> None:
    op.drop_column('group_event_participation', 'created_on')

