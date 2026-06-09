"""add country and city master tables with residence_city_id FK

Revision ID: m014
Revises: m013
Create Date: 2026-06-09
"""

from alembic import op
import sqlalchemy as sa

revision = 'm014'
down_revision = 'm013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'country',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('iso_code', sa.String(length=3), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iso_code'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_country_id'), 'country', ['id'], unique=False)

    op.create_table(
        'city',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('country_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['country_id'], ['country.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('country_id', 'name', name='uq_city_per_country'),
    )
    op.create_index(op.f('ix_city_country_id'), 'city', ['country_id'], unique=False)
    op.create_index(op.f('ix_city_id'), 'city', ['id'], unique=False)

    op.add_column('unit_members', sa.Column('residence_city_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_unit_members_residence_city_id',
        'unit_members',
        'city',
        ['residence_city_id'],
        ['id'],
    )
    op.create_index(op.f('ix_unit_members_residence_city_id'), 'unit_members', ['residence_city_id'], unique=False)

    op.drop_column('unit_members', 'residence_city')
    op.drop_column('unit_members', 'residence_country')


def downgrade() -> None:
    op.add_column('unit_members', sa.Column('residence_country', sa.String(length=100), nullable=True))
    op.add_column('unit_members', sa.Column('residence_city', sa.String(length=100), nullable=True))

    op.drop_constraint('fk_unit_members_residence_city_id', 'unit_members', type_='foreignkey')
    op.drop_index(op.f('ix_unit_members_residence_city_id'), table_name='unit_members')
    op.drop_column('unit_members', 'residence_city_id')

    op.drop_index(op.f('ix_city_id'), table_name='city')
    op.drop_index(op.f('ix_city_country_id'), table_name='city')
    op.drop_table('city')

    op.drop_index(op.f('ix_country_id'), table_name='country')
    op.drop_table('country')
