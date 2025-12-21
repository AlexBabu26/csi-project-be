"""add_gender_seniority_restrictions_to_events

Revision ID: 021cf2b91a60
Revises: 0410cf23be87
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021cf2b91a60'
down_revision = '0410cf23be87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for gender restriction
    gender_enum = sa.Enum('Male', 'Female', name='genderrestriction')
    gender_enum.create(op.get_bind(), checkfirst=True)
    
    # Create separate enum for seniority restriction (different from existing SeniorityCategory)
    seniority_enum = sa.Enum('Junior', 'Senior', name='seniority_restriction_enum')
    seniority_enum.create(op.get_bind(), checkfirst=True)
    
    group_gender_enum = sa.Enum('Male', 'Female', name='group_gender_restriction_enum')
    group_gender_enum.create(op.get_bind(), checkfirst=True)
    
    group_seniority_enum = sa.Enum('Junior', 'Senior', name='group_seniority_restriction_enum')
    group_seniority_enum.create(op.get_bind(), checkfirst=True)
    
    # Add columns to individual_event table
    op.add_column('individual_event',
        sa.Column('gender_restriction', gender_enum, nullable=True)
    )
    op.add_column('individual_event',
        sa.Column('seniority_restriction', seniority_enum, nullable=True)
    )
    
    # Add columns to group_event table
    op.add_column('group_event',
        sa.Column('gender_restriction', group_gender_enum, nullable=True)
    )
    op.add_column('group_event',
        sa.Column('seniority_restriction', group_seniority_enum, nullable=True)
    )


def downgrade() -> None:
    # Drop columns from group_event
    op.drop_column('group_event', 'seniority_restriction')
    op.drop_column('group_event', 'gender_restriction')
    
    # Drop columns from individual_event
    op.drop_column('individual_event', 'seniority_restriction')
    op.drop_column('individual_event', 'gender_restriction')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS group_seniority_restriction_enum')
    op.execute('DROP TYPE IF EXISTS group_gender_restriction_enum')
    op.execute('DROP TYPE IF EXISTS seniority_restriction_enum')
    op.execute('DROP TYPE IF EXISTS genderrestriction')
