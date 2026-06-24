"""add delete reason and notification fields to removed_unit_member

Revision ID: m020
Revises: m019
"""

revision = 'm020'
down_revision = 'm019'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'removed_unit_member',
        sa.Column('delete_reason', sa.Text(), nullable=True),
    )
    op.add_column(
        'removed_unit_member',
        sa.Column('deleted_by_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'removed_unit_member',
        sa.Column('original_member_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'removed_unit_member',
        sa.Column('notified_at', sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        'fk_removed_unit_member_deleted_by_id',
        'removed_unit_member',
        'custom_user',
        ['deleted_by_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_removed_unit_member_deleted_by_id'),
        'removed_unit_member',
        ['deleted_by_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_removed_unit_member_deleted_by_id'),
        table_name='removed_unit_member',
    )
    op.drop_constraint(
        'fk_removed_unit_member_deleted_by_id',
        'removed_unit_member',
        type_='foreignkey',
    )
    op.drop_column('removed_unit_member', 'notified_at')
    op.drop_column('removed_unit_member', 'original_member_id')
    op.drop_column('removed_unit_member', 'deleted_by_id')
    op.drop_column('removed_unit_member', 'delete_reason')
