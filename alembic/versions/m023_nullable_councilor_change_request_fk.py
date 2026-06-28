"""nullable unit_councilor_id on councilor change request with SET NULL on delete

Revision ID: m023
Revises: m022
"""

revision = "m023"
down_revision = "m022"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.drop_constraint(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        type_="foreignkey",
    )
    op.alter_column(
        "unit_councilor_change_request",
        "unit_councilor_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        "unit_councilor",
        ["unit_councilor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        type_="foreignkey",
    )
    op.alter_column(
        "unit_councilor_change_request",
        "unit_councilor_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        "unit_councilor",
        ["unit_councilor_id"],
        ["id"],
    )
