"""add_is_mandatory_and_category_to_events

Revision ID: 0410cf23be87
Revises: 5e2bbf03a6c5
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0410cf23be87'
down_revision = '5e2bbf03a6c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_mandatory column to individual_event table
    op.add_column('individual_event', 
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add category_id and is_mandatory columns to group_event table
    op.add_column('group_event',
        sa.Column('category_id', sa.Integer(), nullable=True)
    )
    op.add_column('group_event',
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add foreign key constraint for category_id in group_event
    op.create_foreign_key(
        'fk_group_event_category_id',
        'group_event', 'event_category',
        ['category_id'], ['id']
    )
    
    # Update per_unit_allowed_limit default to 1 (for group events - 1 group per unit)
    # This is just updating the default, existing data remains unchanged


def downgrade() -> None:
    # Drop foreign key first
    op.drop_constraint('fk_group_event_category_id', 'group_event', type_='foreignkey')
    
    # Drop columns from group_event
    op.drop_column('group_event', 'is_mandatory')
    op.drop_column('group_event', 'category_id')
    
    # Drop column from individual_event
    op.drop_column('individual_event', 'is_mandatory')
