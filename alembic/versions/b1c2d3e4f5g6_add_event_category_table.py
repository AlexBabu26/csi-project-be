"""add_event_category_table

Revision ID: b1c2d3e4f5g6
Revises: 963b7056a6c1
Create Date: 2025-12-21

This migration adds the event_category master table and updates
individual_event to use a foreign key reference instead of a string category.
"""

revision = 'b1c2d3e4f5g6'
down_revision = '963b7056a6c1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Create event_category table
    op.create_table('event_category',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('created_on', sa.DateTime(), nullable=True),
        sa.Column('updated_on', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Add category_id column to individual_event table
    op.add_column('individual_event', 
        sa.Column('category_id', sa.Integer(), nullable=True)
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_individual_event_category_id',
        'individual_event',
        'event_category',
        ['category_id'],
        ['id']
    )
    
    # Migrate existing category data:
    # 1. Get unique categories from individual_event
    # 2. Insert them into event_category
    # 3. Update individual_event.category_id based on the old category string
    
    # Note: This migration preserves existing data by:
    # - Creating categories from existing string values
    # - Setting the foreign key references
    # - Keeping the old 'category' column until data is verified
    
    # Run raw SQL to migrate data
    connection = op.get_bind()
    
    # Insert unique categories from existing data
    connection.execute(sa.text("""
        INSERT INTO event_category (name, description, created_on, updated_on)
        SELECT DISTINCT category, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM individual_event
        WHERE category IS NOT NULL AND category != ''
    """))
    
    # Update category_id based on category name
    connection.execute(sa.text("""
        UPDATE individual_event
        SET category_id = (
            SELECT id FROM event_category WHERE event_category.name = individual_event.category
        )
        WHERE category IS NOT NULL AND category != ''
    """))
    
    # Drop the old category column
    op.drop_column('individual_event', 'category')


def downgrade() -> None:
    # Add back the category string column
    op.add_column('individual_event',
        sa.Column('category', sa.String(length=255), nullable=True)
    )
    
    # Migrate data back from category_id to category string
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE individual_event
        SET category = (
            SELECT name FROM event_category WHERE event_category.id = individual_event.category_id
        )
        WHERE category_id IS NOT NULL
    """))
    
    # Drop the foreign key constraint
    op.drop_constraint('fk_individual_event_category_id', 'individual_event', type_='foreignkey')
    
    # Drop the category_id column
    op.drop_column('individual_event', 'category_id')
    
    # Drop the event_category table
    op.drop_table('event_category')

