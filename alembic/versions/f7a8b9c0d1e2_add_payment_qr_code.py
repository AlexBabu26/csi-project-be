"""Add reusable payment QR code table and link from registration_fee.

Revision ID: f7a8b9c0d1e2_add_payment_qr_code
Revises: add_performance_indexes
Create Date: 2025-12-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2_add_payment_qr_code"
down_revision: Union[str, None] = "add_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create payment_qr_code table and link it from registration_fee."""

    op.create_table(
        "payment_qr_code",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_on", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_on", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "registration_fee",
        sa.Column("qr_code_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_registration_fee_qr_code_id",
        "registration_fee",
        "payment_qr_code",
        ["qr_code_id"],
        ["id"],
    )


def downgrade() -> None:
    """Drop payment_qr_code table and qr_code_id link."""

    op.drop_constraint(
        "fk_registration_fee_qr_code_id",
        "registration_fee",
        type_="foreignkey",
    )
    op.drop_column("registration_fee", "qr_code_id")

    op.drop_table("payment_qr_code")




