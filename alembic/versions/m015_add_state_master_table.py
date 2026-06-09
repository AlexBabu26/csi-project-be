"""add state master table and residence_state_id on unit_members

Revision ID: m015
Revises: m014
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = 'm015'
down_revision = 'm014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['country.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('country_id', 'name', name='uq_state_per_country'),
    )
    op.create_index(op.f('ix_state_country_id'), 'state', ['country_id'], unique=False)
    op.create_index(op.f('ix_state_id'), 'state', ['id'], unique=False)

    op.add_column('city', sa.Column('state_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_city_state_id', 'city', 'state', ['state_id'], ['id'])
    op.create_index(op.f('ix_city_state_id'), 'city', ['state_id'], unique=False)

    op.add_column('unit_members', sa.Column('residence_state_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_unit_members_residence_state_id',
        'unit_members',
        'state',
        ['residence_state_id'],
        ['id'],
    )
    op.create_index(op.f('ix_unit_members_residence_state_id'), 'unit_members', ['residence_state_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_unit_members_residence_state_id', 'unit_members', type_='foreignkey')
    op.drop_index(op.f('ix_unit_members_residence_state_id'), table_name='unit_members')
    op.drop_column('unit_members', 'residence_state_id')

    op.drop_constraint('fk_city_state_id', 'city', type_='foreignkey')
    op.drop_index(op.f('ix_city_state_id'), table_name='city')
    op.drop_column('city', 'state_id')

    op.drop_index(op.f('ix_state_id'), table_name='state')
    op.drop_index(op.f('ix_state_country_id'), table_name='state')
    op.drop_table('state')
