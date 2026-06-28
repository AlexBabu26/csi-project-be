"""snapshot councilor names on change request and drop councilor FK

Revision ID: m024
Revises: m023
"""

revision = "m024"
down_revision = "m023"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "unit_councilor_change_request",
        sa.Column("original_member_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "unit_councilor_change_request",
        sa.Column("new_member_name", sa.String(length=255), nullable=True),
    )

    op.execute(
        """
        UPDATE unit_councilor_change_request cr
        SET original_member_name = om.name
        FROM unit_members om
        WHERE cr.original_unit_member_id = om.id
          AND cr.original_member_name IS NULL
        """
    )
    op.execute(
        """
        UPDATE unit_councilor_change_request cr
        SET new_member_name = nm.name
        FROM unit_members nm
        WHERE cr.unit_member_id = nm.id
          AND cr.new_member_name IS NULL
        """
    )

    op.drop_constraint(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "unit_councilor_change_request_unit_councilor_id_fkey",
        "unit_councilor_change_request",
        "unit_councilor",
        ["unit_councilor_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("unit_councilor_change_request", "new_member_name")
    op.drop_column("unit_councilor_change_request", "original_member_name")
