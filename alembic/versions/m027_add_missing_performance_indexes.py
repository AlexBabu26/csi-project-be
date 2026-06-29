"""Add missing performance indexes for request status, blood group, dob, and composite queries

Revision ID: m027
Revises: m026
Create Date: 2026-06-29
"""

from alembic import op

revision = "m027"
down_revision = "m026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # blood_group: blood donor search filters on this column
    op.create_index(
        "ix_unit_members_blood_group",
        "unit_members",
        ["blood_group"],
        if_not_exists=True,
    )

    # dob: archive-preview and age-based filters scan this column
    op.create_index(
        "ix_unit_members_dob",
        "unit_members",
        ["dob"],
        if_not_exists=True,
    )

    # archived_unit_member.blood_group: blood donor search includes archived members
    op.create_index(
        "ix_archived_unit_member_blood_group",
        "archived_unit_member",
        ["blood_group"],
        if_not_exists=True,
    )

    # Request-table status indexes – dashboard counts PENDING rows on every request type
    op.create_index(
        "ix_unit_member_change_request_status",
        "unit_member_change_request",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_unit_officials_change_request_status",
        "unit_officials_change_request",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_unit_councilor_change_request_status",
        "unit_councilor_change_request",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_unit_member_add_request_status",
        "unit_member_add_request",
        ["status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_archived_member_concern_request_status",
        "archived_member_concern_request",
        ["status"],
        if_not_exists=True,
    )

    # Composite index on registration_cycle (registration_year, status)
    # Used by dashboard completed/in-progress counts and admin unit list
    op.create_index(
        "ix_unit_registration_cycle_year_status",
        "unit_registration_cycle",
        ["registration_year", "status"],
        if_not_exists=True,
    )

    # registration_cycle.registered_user_id: frequently joined/filtered
    op.create_index(
        "ix_unit_registration_cycle_registered_user_id",
        "unit_registration_cycle",
        ["registered_user_id"],
        if_not_exists=True,
    )

    # registration_payment.status: pending payment count in dashboard
    op.create_index(
        "ix_unit_registration_payment_status",
        "unit_registration_payment",
        ["status"],
        if_not_exists=True,
    )

    # registration_payment.registration_cycle_id: payment lookups by cycle
    op.create_index(
        "ix_unit_registration_payment_cycle_id",
        "unit_registration_payment",
        ["registration_cycle_id"],
        if_not_exists=True,
    )

    # Kalamela FK indexes: participation rows are queried by event_id constantly
    op.create_index(
        "ix_individual_event_participation_event_id",
        "individual_event_participation",
        ["individual_event_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_group_event_participation_event_id",
        "group_event_participation",
        ["group_event_id"],
        if_not_exists=True,
    )

    # kalamela_payments.payment_status: admin payment filtering
    op.create_index(
        "ix_kalamela_payments_payment_status",
        "kalamela_payments",
        ["payment_status"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_kalamela_payments_payment_status", table_name="kalamela_payments")
    op.drop_index("ix_group_event_participation_event_id", table_name="group_event_participation")
    op.drop_index("ix_individual_event_participation_event_id", table_name="individual_event_participation")
    op.drop_index("ix_unit_registration_payment_cycle_id", table_name="unit_registration_payment")
    op.drop_index("ix_unit_registration_payment_status", table_name="unit_registration_payment")
    op.drop_index("ix_unit_registration_cycle_registered_user_id", table_name="unit_registration_cycle")
    op.drop_index("ix_unit_registration_cycle_year_status", table_name="unit_registration_cycle")
    op.drop_index("ix_archived_member_concern_request_status", table_name="archived_member_concern_request")
    op.drop_index("ix_unit_member_add_request_status", table_name="unit_member_add_request")
    op.drop_index("ix_unit_councilor_change_request_status", table_name="unit_councilor_change_request")
    op.drop_index("ix_unit_officials_change_request_status", table_name="unit_officials_change_request")
    op.drop_index("ix_unit_member_change_request_status", table_name="unit_member_change_request")
    op.drop_index("ix_archived_unit_member_blood_group", table_name="archived_unit_member")
    op.drop_index("ix_unit_members_dob", table_name="unit_members")
    op.drop_index("ix_unit_members_blood_group", table_name="unit_members")
