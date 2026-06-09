"""add archived_member_concern_request table

Revision ID: m012
Revises: m011
"""

revision = 'm012'
down_revision = 'm011'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


request_status_enum = postgresql.ENUM(
    'PENDING', 'APPROVED', 'REJECTED',
    name='requeststatus',
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        'archived_member_concern_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archived_unit_member_id', sa.Integer(), nullable=False),
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('concern_text', sa.Text(), nullable=False),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('status', request_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['archived_unit_member_id'], ['archived_unit_member.id']),
        sa.ForeignKeyConstraint(['registered_user_id'], ['custom_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_archived_member_concern_request_id'),
        'archived_member_concern_request',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_archived_member_concern_request_archived_unit_member_id'),
        'archived_member_concern_request',
        ['archived_unit_member_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_archived_member_concern_request_registered_user_id'),
        'archived_member_concern_request',
        ['registered_user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_archived_member_concern_request_registered_user_id'),
        table_name='archived_member_concern_request',
    )
    op.drop_index(
        op.f('ix_archived_member_concern_request_archived_unit_member_id'),
        table_name='archived_member_concern_request',
    )
    op.drop_index(
        op.f('ix_archived_member_concern_request_id'),
        table_name='archived_member_concern_request',
    )
    op.drop_table('archived_member_concern_request')
