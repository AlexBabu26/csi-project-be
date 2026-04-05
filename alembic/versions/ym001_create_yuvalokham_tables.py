"""create yuvalokham tables"""

revision = 'ym001'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table('ym_magazine',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('issue_number', sa.String(length=50), nullable=True),
        sa.Column('volume', sa.String(length=50), nullable=True),
        sa.Column('cover_image_url', sa.String(length=500), nullable=True),
        sa.Column('pdf_file_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'published', name='magazinestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_magazine_id'), 'ym_magazine', ['id'], unique=False)

    op.create_table('ym_subscription_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('duration_months', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_subscription_plan_id'), 'ym_subscription_plan', ['id'], unique=False)

    op.create_table('ym_user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', name='yuvalokhamuserrole'), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('pincode', sa.String(length=10), nullable=True),
        sa.Column('district_id', sa.Integer(), nullable=True),
        sa.Column('unit_id', sa.Integer(), nullable=True),
        sa.Column('parish_name', sa.String(length=255), nullable=True),
        sa.Column('is_csi_member', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['district_id'], ['clergy_district.id']),
        sa.ForeignKeyConstraint(['unit_id'], ['unit_name.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_ym_user_email'), 'ym_user', ['email'], unique=True)
    op.create_index(op.f('ix_ym_user_id'), 'ym_user', ['id'], unique=False)

    op.create_table('ym_complaint',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('delivery_issue', 'payment_dispute', 'content_issue', 'subscription_problem', 'other', name='complaintcategory'), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('open', 'resolved', 'closed', name='complaintstatus'), nullable=False),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('responded_by', sa.Integer(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['responded_by'], ['ym_user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['ym_user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_complaint_id'), 'ym_complaint', ['id'], unique=False)
    op.create_index(op.f('ix_ym_complaint_user_id'), 'ym_complaint', ['user_id'], unique=False)

    op.create_table('ym_qr_setting',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('qr_image_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['ym_user.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('ym_refresh_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['ym_user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_refresh_token_id'), 'ym_refresh_token', ['id'], unique=False)
    op.create_index(op.f('ix_ym_refresh_token_token'), 'ym_refresh_token', ['token'], unique=False)

    op.create_table('ym_subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('plan_name_snapshot', sa.String(length=150), nullable=False),
        sa.Column('plan_price_snapshot', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('plan_duration_snapshot', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('active', 'expired', 'pending_payment', name='subscriptionstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['ym_subscription_plan.id']),
        sa.ForeignKeyConstraint(['user_id'], ['ym_user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_subscription_id'), 'ym_subscription', ['id'], unique=False)
    op.create_index(op.f('ix_ym_subscription_user_id'), 'ym_subscription', ['user_id'], unique=False)

    op.create_table('ym_payment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('proof_file_url', sa.String(length=500), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='ympaymentstatus'), nullable=False),
        sa.Column('admin_remarks', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reviewed_by'], ['ym_user.id']),
        sa.ForeignKeyConstraint(['subscription_id'], ['ym_subscription.id']),
        sa.ForeignKeyConstraint(['user_id'], ['ym_user.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ym_payment_id'), 'ym_payment', ['id'], unique=False)
    op.create_index(op.f('ix_ym_payment_user_id'), 'ym_payment', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ym_payment_user_id'), table_name='ym_payment')
    op.drop_index(op.f('ix_ym_payment_id'), table_name='ym_payment')
    op.drop_table('ym_payment')
    op.drop_index(op.f('ix_ym_subscription_user_id'), table_name='ym_subscription')
    op.drop_index(op.f('ix_ym_subscription_id'), table_name='ym_subscription')
    op.drop_table('ym_subscription')
    op.drop_index(op.f('ix_ym_refresh_token_token'), table_name='ym_refresh_token')
    op.drop_index(op.f('ix_ym_refresh_token_id'), table_name='ym_refresh_token')
    op.drop_table('ym_refresh_token')
    op.drop_table('ym_qr_setting')
    op.drop_index(op.f('ix_ym_complaint_user_id'), table_name='ym_complaint')
    op.drop_index(op.f('ix_ym_complaint_id'), table_name='ym_complaint')
    op.drop_table('ym_complaint')
    op.drop_index(op.f('ix_ym_user_id'), table_name='ym_user')
    op.drop_index(op.f('ix_ym_user_email'), table_name='ym_user')
    op.drop_table('ym_user')
    op.drop_index(op.f('ix_ym_subscription_plan_id'), table_name='ym_subscription_plan')
    op.drop_table('ym_subscription_plan')
    op.drop_index(op.f('ix_ym_magazine_id'), table_name='ym_magazine')
    op.drop_table('ym_magazine')

    sa.Enum('draft', 'published', name='magazinestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum('admin', 'user', name='yuvalokhamuserrole').drop(op.get_bind(), checkfirst=True)
    sa.Enum('delivery_issue', 'payment_dispute', 'content_issue', 'subscription_problem', 'other', name='complaintcategory').drop(op.get_bind(), checkfirst=True)
    sa.Enum('open', 'resolved', 'closed', name='complaintstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum('active', 'expired', 'pending_payment', name='subscriptionstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum('pending', 'approved', 'rejected', name='ympaymentstatus').drop(op.get_bind(), checkfirst=True)
