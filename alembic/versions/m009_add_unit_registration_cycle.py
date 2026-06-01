"""add unit_registration_cycle, current_registration_year, payment cycle FK

Revision ID: m009
Revises: m008
"""

revision = 'm009'
down_revision = 'm008'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        'unit_registration_cycle',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('registered_user_id', sa.Integer(), sa.ForeignKey('custom_user.id'), nullable=False, index=True),
        sa.Column('registration_year', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(64), nullable=False, server_default='Registration Started'),
        sa.Column('path_type', sa.String(16), nullable=False, server_default='fresh'),
        sa.Column('member_count_at_submit', sa.Integer(), nullable=True),
        sa.Column('total_fee_at_submit', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            'registered_user_id',
            'registration_year',
            name='uq_unit_registration_cycle_user_year',
        ),
    )

    op.add_column(
        'site_settings',
        sa.Column('current_registration_year', sa.Integer(), nullable=True, server_default='2025'),
    )

    op.add_column(
        'unit_registration_payment',
        sa.Column(
            'registration_cycle_id',
            sa.Integer(),
            sa.ForeignKey('unit_registration_cycle.id'),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('unit_registration_payment', 'registration_cycle_id')
    op.drop_column('site_settings', 'current_registration_year')
    op.drop_table('unit_registration_cycle')
