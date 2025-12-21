"""add_kalamela_rules_table

Revision ID: 5e2bbf03a6c5
Revises: badd61afa808
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e2bbf03a6c5'
down_revision = 'badd61afa808'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create kalamela_rules table
    op.create_table('kalamela_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_key', sa.String(length=100), nullable=False),
        sa.Column('rule_category', sa.Enum('age_restriction', 'participation_limit', 'fee', name='rulecategory'), nullable=False),
        sa.Column('rule_value', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_on', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_on', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['custom_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kalamela_rules_rule_key'), 'kalamela_rules', ['rule_key'], unique=True)
    
    # Insert default rules
    op.execute("""
        INSERT INTO kalamela_rules (rule_key, rule_category, rule_value, display_name, description, is_active) VALUES
        ('senior_dob_start', 'age_restriction', '1991-01-11', 'Senior DOB Start', 'Earliest date of birth for Senior category (21-34 years old)', true),
        ('senior_dob_end', 'age_restriction', '2005-01-10', 'Senior DOB End', 'Latest date of birth for Senior category', true),
        ('junior_dob_start', 'age_restriction', '2005-01-11', 'Junior DOB Start', 'Earliest date of birth for Junior category (14-20 years old)', true),
        ('junior_dob_end', 'age_restriction', '2011-06-30', 'Junior DOB End', 'Latest date of birth for Junior category', true),
        ('max_individual_events_per_person', 'participation_limit', '5', 'Max Individual Events Per Person', 'Maximum number of individual events a person can participate in', true),
        ('max_participants_per_unit_per_event', 'participation_limit', '2', 'Max Participants Per Unit Per Event', 'Maximum participants from one unit in a single individual event', true),
        ('max_groups_per_unit_per_group_event', 'participation_limit', '1', 'Max Groups Per Unit Per Group Event', 'Maximum groups from one unit in a single group event', true),
        ('individual_event_fee', 'fee', '50', 'Individual Event Fee', 'Registration fee per individual event participation (in rupees)', true),
        ('group_event_fee', 'fee', '100', 'Group Event Fee', 'Registration fee per group event participation (in rupees)', true),
        ('appeal_fee', 'fee', '1000', 'Appeal Fee', 'Fee for submitting an appeal (in rupees)', true)
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_kalamela_rules_rule_key'), table_name='kalamela_rules')
    op.drop_table('kalamela_rules')
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS rulecategory")
