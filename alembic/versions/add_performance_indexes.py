"""Add performance indexes for frequently queried columns

Revision ID: add_performance_indexes
Revises: a076b7859c09
Create Date: 2024-12-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = 'a076b7859c09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for frequently queried columns to improve performance."""
    
    # Index on unit_members.registered_user_id (frequently joined)
    op.create_index(
        'ix_unit_members_registered_user_id',
        'unit_members',
        ['registered_user_id'],
        if_not_exists=True
    )
    
    # Index on unit_members.gender (frequently filtered)
    op.create_index(
        'ix_unit_members_gender',
        'unit_members',
        ['gender'],
        if_not_exists=True
    )
    
    # Index on custom_user.unit_name_id (frequently joined)
    op.create_index(
        'ix_custom_user_unit_name_id',
        'custom_user',
        ['unit_name_id'],
        if_not_exists=True
    )
    
    # Index on custom_user.user_type (frequently filtered)
    op.create_index(
        'ix_custom_user_user_type',
        'custom_user',
        ['user_type'],
        if_not_exists=True
    )
    
    # Index on unit_registration_data.status (frequently filtered)
    op.create_index(
        'ix_unit_registration_data_status',
        'unit_registration_data',
        ['status'],
        if_not_exists=True
    )
    
    # Index on unit_registration_data.registered_user_id (frequently joined)
    op.create_index(
        'ix_unit_registration_data_registered_user_id',
        'unit_registration_data',
        ['registered_user_id'],
        if_not_exists=True
    )
    
    # Index on unit_name.clergy_district_id (frequently joined)
    op.create_index(
        'ix_unit_name_clergy_district_id',
        'unit_name',
        ['clergy_district_id'],
        if_not_exists=True
    )
    
    # Index on unit_transfer_request.original_registered_user_id
    op.create_index(
        'ix_unit_transfer_request_original_user_id',
        'unit_transfer_request',
        ['original_registered_user_id'],
        if_not_exists=True
    )
    
    # Index on unit_transfer_request.status
    op.create_index(
        'ix_unit_transfer_request_status',
        'unit_transfer_request',
        ['status'],
        if_not_exists=True
    )
    
    # Index on archived_unit_member.archived_at (frequently ordered)
    op.create_index(
        'ix_archived_unit_member_archived_at',
        'archived_unit_member',
        ['archived_at'],
        if_not_exists=True
    )


def downgrade() -> None:
    """Remove the performance indexes."""
    
    op.drop_index('ix_archived_unit_member_archived_at', table_name='archived_unit_member')
    op.drop_index('ix_unit_transfer_request_status', table_name='unit_transfer_request')
    op.drop_index('ix_unit_transfer_request_original_user_id', table_name='unit_transfer_request')
    op.drop_index('ix_unit_name_clergy_district_id', table_name='unit_name')
    op.drop_index('ix_unit_registration_data_registered_user_id', table_name='unit_registration_data')
    op.drop_index('ix_unit_registration_data_status', table_name='unit_registration_data')
    op.drop_index('ix_custom_user_user_type', table_name='custom_user')
    op.drop_index('ix_custom_user_unit_name_id', table_name='custom_user')
    op.drop_index('ix_unit_members_gender', table_name='unit_members')
    op.drop_index('ix_unit_members_registered_user_id', table_name='unit_members')

