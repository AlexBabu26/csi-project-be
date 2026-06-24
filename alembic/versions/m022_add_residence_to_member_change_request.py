"""add residence fields to unit_member_change_request

Revision ID: m022
Revises: m021
"""

revision = 'm022'
down_revision = 'm021'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    residence_location_enum = sa.Enum(
        'WITHIN_KERALA',
        'OUTSIDE_KERALA',
        'OUTSIDE_INDIA',
        name='residencelocation',
        create_type=False,
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('residence_location', residence_location_enum, nullable=True),
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('residence_state_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('residence_city_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('original_residence_location', residence_location_enum, nullable=True),
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('original_residence_state_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'unit_member_change_request',
        sa.Column('original_residence_city_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_unit_member_change_request_residence_state_id',
        'unit_member_change_request',
        'state',
        ['residence_state_id'],
        ['id'],
    )
    op.create_foreign_key(
        'fk_unit_member_change_request_residence_city_id',
        'unit_member_change_request',
        'city',
        ['residence_city_id'],
        ['id'],
    )
    op.create_foreign_key(
        'fk_unit_member_change_request_original_residence_state_id',
        'unit_member_change_request',
        'state',
        ['original_residence_state_id'],
        ['id'],
    )
    op.create_foreign_key(
        'fk_unit_member_change_request_original_residence_city_id',
        'unit_member_change_request',
        'city',
        ['original_residence_city_id'],
        ['id'],
    )
    op.create_index(
        op.f('ix_unit_member_change_request_residence_state_id'),
        'unit_member_change_request',
        ['residence_state_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_unit_member_change_request_residence_city_id'),
        'unit_member_change_request',
        ['residence_city_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_unit_member_change_request_residence_city_id'),
        table_name='unit_member_change_request',
    )
    op.drop_index(
        op.f('ix_unit_member_change_request_residence_state_id'),
        table_name='unit_member_change_request',
    )
    op.drop_constraint(
        'fk_unit_member_change_request_original_residence_city_id',
        'unit_member_change_request',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_unit_member_change_request_original_residence_state_id',
        'unit_member_change_request',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_unit_member_change_request_residence_city_id',
        'unit_member_change_request',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_unit_member_change_request_residence_state_id',
        'unit_member_change_request',
        type_='foreignkey',
    )
    op.drop_column('unit_member_change_request', 'original_residence_city_id')
    op.drop_column('unit_member_change_request', 'original_residence_state_id')
    op.drop_column('unit_member_change_request', 'original_residence_location')
    op.drop_column('unit_member_change_request', 'residence_city_id')
    op.drop_column('unit_member_change_request', 'residence_state_id')
    op.drop_column('unit_member_change_request', 'residence_location')
