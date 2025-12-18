"""add_missing_unit_and_conference_tables

Revision ID: 963b7056a6c1
Revises: a076b7859c09
Create Date: 2024-12-18

This migration adds the 8 missing tables that exist in FastAPI models
but were not created in the database.
"""

revision = '963b7056a6c1'
down_revision = 'a076b7859c09'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Create archived_unit_member table
    op.create_table('archived_unit_member',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('number', sa.String(length=30), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['registered_user_id'], ['custom_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_archived_unit_member_id'), 'archived_unit_member', ['id'], unique=False)
    op.create_index(op.f('ix_archived_unit_member_registered_user_id'), 'archived_unit_member', ['registered_user_id'], unique=False)

    # Create removed_unit_member table
    op.create_table('removed_unit_member',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('number', sa.String(length=30), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['registered_user_id'], ['custom_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_removed_unit_member_id'), 'removed_unit_member', ['id'], unique=False)
    op.create_index(op.f('ix_removed_unit_member_registered_user_id'), 'removed_unit_member', ['registered_user_id'], unique=False)

    # Create food_preference table
    op.create_table('food_preference',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conference_id', sa.Integer(), nullable=False),
        sa.Column('veg_count', sa.Integer(), nullable=True),
        sa.Column('non_veg_count', sa.Integer(), nullable=True),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conference_id'], ['conference.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['custom_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_food_preference_id'), 'food_preference', ['id'], unique=False)
    op.create_index(op.f('ix_food_preference_conference_id'), 'food_preference', ['conference_id'], unique=False)
    op.create_index(op.f('ix_food_preference_uploaded_by_id'), 'food_preference', ['uploaded_by_id'], unique=False)

    # Create unit_transfer_request table
    op.create_table('unit_transfer_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_member_id', sa.Integer(), nullable=False),
        sa.Column('current_unit_id', sa.Integer(), nullable=True),
        sa.Column('original_registered_user_id', sa.Integer(), nullable=True),
        sa.Column('destination_unit_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proof', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['current_unit_id'], ['unit_name.id'], ),
        sa.ForeignKeyConstraint(['destination_unit_id'], ['unit_name.id'], ),
        sa.ForeignKeyConstraint(['original_registered_user_id'], ['custom_user.id'], ),
        sa.ForeignKeyConstraint(['unit_member_id'], ['unit_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_transfer_request_id'), 'unit_transfer_request', ['id'], unique=False)
    op.create_index(op.f('ix_unit_transfer_request_unit_member_id'), 'unit_transfer_request', ['unit_member_id'], unique=False)

    # Create unit_member_change_request table
    op.create_table('unit_member_change_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_member_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('dob', sa.Date(), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('original_name', sa.String(length=255), nullable=True),
        sa.Column('original_gender', sa.String(length=10), nullable=True),
        sa.Column('original_dob', sa.Date(), nullable=True),
        sa.Column('original_blood_group', sa.String(length=10), nullable=True),
        sa.Column('original_qualification', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proof', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['unit_member_id'], ['unit_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_member_change_request_id'), 'unit_member_change_request', ['id'], unique=False)
    op.create_index(op.f('ix_unit_member_change_request_unit_member_id'), 'unit_member_change_request', ['unit_member_id'], unique=False)

    # Create unit_member_add_request table
    op.create_table('unit_member_add_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registered_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=False),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('number', sa.String(length=30), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proof', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['registered_user_id'], ['custom_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_member_add_request_id'), 'unit_member_add_request', ['id'], unique=False)
    op.create_index(op.f('ix_unit_member_add_request_registered_user_id'), 'unit_member_add_request', ['registered_user_id'], unique=False)

    # Create unit_officials_change_request table
    op.create_table('unit_officials_change_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_official_id', sa.Integer(), nullable=False),
        sa.Column('president_designation', sa.String(length=50), nullable=True),
        sa.Column('original_president_designation', sa.String(length=50), nullable=True),
        sa.Column('president_name', sa.String(length=255), nullable=True),
        sa.Column('original_president_name', sa.String(length=255), nullable=True),
        sa.Column('president_phone', sa.String(length=30), nullable=True),
        sa.Column('original_president_phone', sa.String(length=30), nullable=True),
        sa.Column('vice_president_name', sa.String(length=255), nullable=True),
        sa.Column('original_vice_president_name', sa.String(length=255), nullable=True),
        sa.Column('vice_president_phone', sa.String(length=30), nullable=True),
        sa.Column('original_vice_president_phone', sa.String(length=30), nullable=True),
        sa.Column('secretary_name', sa.String(length=255), nullable=True),
        sa.Column('original_secretary_name', sa.String(length=255), nullable=True),
        sa.Column('secretary_phone', sa.String(length=30), nullable=True),
        sa.Column('original_secretary_phone', sa.String(length=30), nullable=True),
        sa.Column('joint_secretary_name', sa.String(length=255), nullable=True),
        sa.Column('original_joint_secretary_name', sa.String(length=255), nullable=True),
        sa.Column('joint_secretary_phone', sa.String(length=30), nullable=True),
        sa.Column('original_joint_secretary_phone', sa.String(length=30), nullable=True),
        sa.Column('treasurer_name', sa.String(length=255), nullable=True),
        sa.Column('original_treasurer_name', sa.String(length=255), nullable=True),
        sa.Column('treasurer_phone', sa.String(length=30), nullable=True),
        sa.Column('original_treasurer_phone', sa.String(length=30), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proof', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['unit_official_id'], ['unit_officials.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_officials_change_request_id'), 'unit_officials_change_request', ['id'], unique=False)
    op.create_index(op.f('ix_unit_officials_change_request_unit_official_id'), 'unit_officials_change_request', ['unit_official_id'], unique=False)

    # Create unit_councilor_change_request table
    op.create_table('unit_councilor_change_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_councilor_id', sa.Integer(), nullable=False),
        sa.Column('unit_member_id', sa.Integer(), nullable=True),
        sa.Column('original_unit_member_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proof', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['original_unit_member_id'], ['unit_members.id'], ),
        sa.ForeignKeyConstraint(['unit_councilor_id'], ['unit_councilor.id'], ),
        sa.ForeignKeyConstraint(['unit_member_id'], ['unit_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_councilor_change_request_id'), 'unit_councilor_change_request', ['id'], unique=False)
    op.create_index(op.f('ix_unit_councilor_change_request_unit_councilor_id'), 'unit_councilor_change_request', ['unit_councilor_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_unit_councilor_change_request_unit_councilor_id'), table_name='unit_councilor_change_request')
    op.drop_index(op.f('ix_unit_councilor_change_request_id'), table_name='unit_councilor_change_request')
    op.drop_table('unit_councilor_change_request')

    op.drop_index(op.f('ix_unit_officials_change_request_unit_official_id'), table_name='unit_officials_change_request')
    op.drop_index(op.f('ix_unit_officials_change_request_id'), table_name='unit_officials_change_request')
    op.drop_table('unit_officials_change_request')

    op.drop_index(op.f('ix_unit_member_add_request_registered_user_id'), table_name='unit_member_add_request')
    op.drop_index(op.f('ix_unit_member_add_request_id'), table_name='unit_member_add_request')
    op.drop_table('unit_member_add_request')

    op.drop_index(op.f('ix_unit_member_change_request_unit_member_id'), table_name='unit_member_change_request')
    op.drop_index(op.f('ix_unit_member_change_request_id'), table_name='unit_member_change_request')
    op.drop_table('unit_member_change_request')

    op.drop_index(op.f('ix_unit_transfer_request_unit_member_id'), table_name='unit_transfer_request')
    op.drop_index(op.f('ix_unit_transfer_request_id'), table_name='unit_transfer_request')
    op.drop_table('unit_transfer_request')

    op.drop_index(op.f('ix_food_preference_uploaded_by_id'), table_name='food_preference')
    op.drop_index(op.f('ix_food_preference_conference_id'), table_name='food_preference')
    op.drop_index(op.f('ix_food_preference_id'), table_name='food_preference')
    op.drop_table('food_preference')

    op.drop_index(op.f('ix_removed_unit_member_registered_user_id'), table_name='removed_unit_member')
    op.drop_index(op.f('ix_removed_unit_member_id'), table_name='removed_unit_member')
    op.drop_table('removed_unit_member')

    op.drop_index(op.f('ix_archived_unit_member_registered_user_id'), table_name='archived_unit_member')
    op.drop_index(op.f('ix_archived_unit_member_id'), table_name='archived_unit_member')
    op.drop_table('archived_unit_member')
