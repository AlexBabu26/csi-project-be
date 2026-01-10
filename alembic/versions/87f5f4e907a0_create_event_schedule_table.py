"""create_event_schedule_table

Revision ID: 87f5f4e907a0
Revises: 458de5c74b1e
Create Date: 2025-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '87f5f4e907a0'
down_revision = '458de5c74b1e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create event_schedule table with ScheduleStatus enum."""
    
    # Create ScheduleStatus enum only if it doesn't exist (using raw SQL)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE schedulestatus AS ENUM ('Scheduled', 'Ongoing', 'Completed', 'Cancelled', 'Postponed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Reference existing EventType enum (don't create it, it already exists)
    # Use postgresql.ENUM to reference the existing type
    event_type_enum = postgresql.ENUM('individual', 'group', name='eventtype', create_type=False)
    
    # Reference ScheduleStatus enum (don't create it, we already did above)
    schedule_status_enum = postgresql.ENUM(
        'Scheduled',
        'Ongoing',
        'Completed',
        'Cancelled',
        'Postponed',
        name='schedulestatus',
        create_type=False
    )
    
    # Create event_schedule table
    op.create_table(
        'event_schedule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('event_type', event_type_enum, nullable=False),
        sa.Column('stage_name', sa.String(length=255), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', schedule_status_enum, nullable=False, server_default='Scheduled'),
        sa.Column('created_on', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_on', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['custom_user.id'], ),
    )
    
    # Create indexes for better query performance
    op.create_index('ix_event_schedule_event_id_type', 'event_schedule', ['event_id', 'event_type'])
    op.create_index('ix_event_schedule_stage_name', 'event_schedule', ['stage_name'])
    op.create_index('ix_event_schedule_start_time', 'event_schedule', ['start_time'])
    op.create_index('ix_event_schedule_end_time', 'event_schedule', ['end_time'])
    op.create_index('ix_event_schedule_status', 'event_schedule', ['status'])


def downgrade() -> None:
    """Drop event_schedule table and ScheduleStatus enum."""
    
    # Drop indexes
    op.drop_index('ix_event_schedule_status', table_name='event_schedule')
    op.drop_index('ix_event_schedule_end_time', table_name='event_schedule')
    op.drop_index('ix_event_schedule_start_time', table_name='event_schedule')
    op.drop_index('ix_event_schedule_stage_name', table_name='event_schedule')
    op.drop_index('ix_event_schedule_event_id_type', table_name='event_schedule')
    
    # Drop table
    op.drop_table('event_schedule')
    
    # Drop enum types (only ScheduleStatus, EventType should remain)
    op.execute('DROP TYPE IF EXISTS schedulestatus')