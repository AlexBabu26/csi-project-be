"""change_awarded_mark_to_decimal

Revision ID: a1b2c3d4e5f6
Revises: 87f5f4e907a0
Create Date: 2025-01-10 16:03:09.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '87f5f4e907a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change awarded_mark columns from Integer to Numeric(5,2) to support decimal values."""
    
    # Alter individual_event_score_card.awarded_mark
    op.alter_column(
        'individual_event_score_card',
        'awarded_mark',
        existing_type=sa.Integer(),
        type_=sa.Numeric(5, 2),
        existing_nullable=False,
        existing_server_default=sa.text('0'),
        server_default=sa.text('0.0'),
        postgresql_using='awarded_mark::numeric(5,2)'
    )
    
    # Alter group_event_score_card.awarded_mark
    op.alter_column(
        'group_event_score_card',
        'awarded_mark',
        existing_type=sa.Integer(),
        type_=sa.Numeric(5, 2),
        existing_nullable=False,
        existing_server_default=sa.text('0'),
        server_default=sa.text('0.0'),
        postgresql_using='awarded_mark::numeric(5,2)'
    )


def downgrade() -> None:
    """Revert awarded_mark columns back to Integer."""
    
    # Revert individual_event_score_card.awarded_mark
    op.alter_column(
        'individual_event_score_card',
        'awarded_mark',
        existing_type=sa.Numeric(5, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default=sa.text('0.0'),
        server_default=sa.text('0'),
        postgresql_using='ROUND(awarded_mark)::integer'
    )
    
    # Revert group_event_score_card.awarded_mark
    op.alter_column(
        'group_event_score_card',
        'awarded_mark',
        existing_type=sa.Numeric(5, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default=sa.text('0.0'),
        server_default=sa.text('0'),
        postgresql_using='ROUND(awarded_mark)::integer'
    )

