"""add removal_type to distinguish admin removal from archival records

Revision ID: m021
Revises: m020
"""

revision = 'm021'
down_revision = 'm020'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    removal_type_enum = sa.Enum('ADMIN', 'LEGACY', name='memberremovaltype')
    removal_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'removed_unit_member',
        sa.Column(
            'removal_type',
            removal_type_enum,
            nullable=False,
            server_default='LEGACY',
        ),
    )

    # Rows created by the admin remove flow include delete_reason
    op.execute(
        "UPDATE removed_unit_member SET removal_type = 'ADMIN' WHERE delete_reason IS NOT NULL"
    )

    op.alter_column('removed_unit_member', 'removal_type', server_default=None)


def downgrade() -> None:
    op.drop_column('removed_unit_member', 'removal_type')
    sa.Enum(name='memberremovaltype').drop(op.get_bind(), checkfirst=True)
