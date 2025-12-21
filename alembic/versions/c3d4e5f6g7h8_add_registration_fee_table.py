"""add_registration_fee_table

Revision ID: c3d4e5f6g7h8
Revises: b1c2d3e4f5g6
Create Date: 2025-12-21

This migration adds the registration_fee master table and updates
individual_event and group_event tables with foreign key references.
"""

revision = 'c3d4e5f6g7h8'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Create registration_fee table
    op.create_table('registration_fee',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.Enum('individual', 'group', name='eventtype'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.Column('created_on', sa.DateTime(), nullable=True),
        sa.Column('updated_on', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['created_by_id'], ['custom_user.id'], ),
        sa.ForeignKeyConstraint(['updated_by_id'], ['custom_user.id'], ),
    )
    
    # Add registration_fee_id column to individual_event table
    op.add_column('individual_event', 
        sa.Column('registration_fee_id', sa.Integer(), nullable=True)
    )
    
    # Create foreign key constraint for individual_event
    op.create_foreign_key(
        'fk_individual_event_registration_fee_id',
        'individual_event',
        'registration_fee',
        ['registration_fee_id'],
        ['id']
    )
    
    # Add registration_fee_id column to group_event table
    op.add_column('group_event', 
        sa.Column('registration_fee_id', sa.Integer(), nullable=True)
    )
    
    # Create foreign key constraint for group_event
    op.create_foreign_key(
        'fk_group_event_registration_fee_id',
        'group_event',
        'registration_fee',
        ['registration_fee_id'],
        ['id']
    )
    
    # Insert default registration fees
    connection = op.get_bind()
    
    # Insert default individual event fee (₹50)
    connection.execute(sa.text("""
        INSERT INTO registration_fee (name, event_type, amount, created_on, updated_on)
        VALUES ('Individual Event Fee', 'individual', 50, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """))
    
    # Insert default group event fee (₹100)
    connection.execute(sa.text("""
        INSERT INTO registration_fee (name, event_type, amount, created_on, updated_on)
        VALUES ('Group Event Fee', 'group', 100, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """))


def downgrade() -> None:
    # Drop foreign key constraint from group_event
    op.drop_constraint('fk_group_event_registration_fee_id', 'group_event', type_='foreignkey')
    
    # Drop registration_fee_id column from group_event
    op.drop_column('group_event', 'registration_fee_id')
    
    # Drop foreign key constraint from individual_event
    op.drop_constraint('fk_individual_event_registration_fee_id', 'individual_event', type_='foreignkey')
    
    # Drop registration_fee_id column from individual_event
    op.drop_column('individual_event', 'registration_fee_id')
    
    # Drop the registration_fee table
    op.drop_table('registration_fee')
    
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS eventtype')

