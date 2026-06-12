"""add added_registration_cycle_id to unit_members

Revision ID: m018
Revises: m017
"""

revision = 'm018'
down_revision = 'm017'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'unit_members',
        sa.Column('added_registration_cycle_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_unit_members_added_registration_cycle_id',
        'unit_members',
        'unit_registration_cycle',
        ['added_registration_cycle_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_unit_members_added_registration_cycle_id'),
        'unit_members',
        ['added_registration_cycle_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_unit_members_added_registration_cycle_id'), table_name='unit_members')
    op.drop_constraint('fk_unit_members_added_registration_cycle_id', 'unit_members', type_='foreignkey')
    op.drop_column('unit_members', 'added_registration_cycle_id')
