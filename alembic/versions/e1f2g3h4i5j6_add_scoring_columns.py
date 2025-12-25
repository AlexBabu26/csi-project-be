"""Add scoring columns for auto-calculation

Adds grade_points, rank, rank_points columns to score card tables
for the new auto-calculation scoring system.

Revision ID: e1f2g3h4i5j6
Revises: d5a945c7bfca
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = 'd5a945c7bfca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to individual_event_score_card
    op.add_column('individual_event_score_card', 
        sa.Column('grade_points', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('individual_event_score_card', 
        sa.Column('rank', sa.Integer(), nullable=True))
    op.add_column('individual_event_score_card', 
        sa.Column('rank_points', sa.Integer(), nullable=True, server_default='0'))
    
    # Add new columns to group_event_score_card
    op.add_column('group_event_score_card', 
        sa.Column('grade_points', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('group_event_score_card', 
        sa.Column('rank', sa.Integer(), nullable=True))
    op.add_column('group_event_score_card', 
        sa.Column('rank_points', sa.Integer(), nullable=True, server_default='0'))
    
    # Update existing records with calculated values
    # For individual scores: calculate grade_points based on awarded_mark
    op.execute("""
        UPDATE individual_event_score_card 
        SET grade_points = CASE 
            WHEN awarded_mark >= 60 THEN 5
            WHEN awarded_mark >= 50 THEN 3
            WHEN awarded_mark >= 40 THEN 1
            ELSE 0
        END
    """)
    
    # For group scores: calculate grade_points based on awarded_mark
    op.execute("""
        UPDATE group_event_score_card 
        SET grade_points = CASE 
            WHEN awarded_mark >= 60 THEN 5
            WHEN awarded_mark >= 50 THEN 3
            WHEN awarded_mark >= 40 THEN 1
            ELSE 0
        END
    """)
    
    # Modify grade column to be single character (A, B, C)
    # First update existing grades to single character
    op.execute("""
        UPDATE individual_event_score_card 
        SET grade = CASE 
            WHEN awarded_mark >= 60 THEN 'A'
            WHEN awarded_mark >= 50 THEN 'B'
            WHEN awarded_mark >= 40 THEN 'C'
            ELSE NULL
        END
    """)
    
    op.execute("""
        UPDATE group_event_score_card 
        SET grade = CASE 
            WHEN awarded_mark >= 60 THEN 'A'
            WHEN awarded_mark >= 50 THEN 'B'
            WHEN awarded_mark >= 40 THEN 'C'
            ELSE NULL
        END
    """)
    
    # Set default values for new columns
    op.alter_column('individual_event_score_card', 'grade_points',
        existing_type=sa.Integer(),
        server_default='0',
        nullable=False)
    op.alter_column('individual_event_score_card', 'rank_points',
        existing_type=sa.Integer(),
        server_default='0',
        nullable=False)
    
    op.alter_column('group_event_score_card', 'grade_points',
        existing_type=sa.Integer(),
        server_default='0',
        nullable=False)
    op.alter_column('group_event_score_card', 'rank_points',
        existing_type=sa.Integer(),
        server_default='0',
        nullable=False)


def downgrade() -> None:
    # Remove columns from individual_event_score_card
    op.drop_column('individual_event_score_card', 'rank_points')
    op.drop_column('individual_event_score_card', 'rank')
    op.drop_column('individual_event_score_card', 'grade_points')
    
    # Remove columns from group_event_score_card
    op.drop_column('group_event_score_card', 'rank_points')
    op.drop_column('group_event_score_card', 'rank')
    op.drop_column('group_event_score_card', 'grade_points')

