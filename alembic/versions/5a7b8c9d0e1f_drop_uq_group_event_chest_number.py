"""drop_uq_group_event_chest_number_constraint

Revision ID: 5a7b8c9d0e1f
Revises: 4efd66ecfc7c
Create Date: 2025-12-24

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '5a7b8c9d0e1f'
down_revision = '4efd66ecfc7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint on (group_event_id, chest_number)
    # This constraint was incorrect because group events allow multiple participants
    # to share the same chest number (they're on the same team)
    op.drop_constraint('uq_group_event_chest_number', 'group_event_participation', type_='unique')


def downgrade() -> None:
    # Re-add the constraint if needed (though this would break group events)
    op.create_unique_constraint('uq_group_event_chest_number', 'group_event_participation', ['group_event_id', 'chest_number'])

