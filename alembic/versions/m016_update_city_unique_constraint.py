"""update city uniqueness to support country-state-city hierarchy

Revision ID: m016
Revises: m015
Create Date: 2026-06-09
"""

from alembic import op

revision = 'm016'
down_revision = 'm015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_city_per_country', 'city', type_='unique')
    op.create_unique_constraint('uq_city_per_state', 'city', ['state_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_city_per_state', 'city', type_='unique')
    op.create_unique_constraint('uq_city_per_country', 'city', ['country_id', 'name'])
