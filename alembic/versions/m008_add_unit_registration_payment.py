"""add unit_registration_payment table and payment_qr_url to site_settings

Revision ID: m008
Revises: m007
"""

revision = 'm008'
down_revision = 'm007'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Add payment QR column to site_settings
    op.add_column(
        'site_settings',
        sa.Column('payment_qr_url', sa.String(500), nullable=True),
    )

    # Create unit registration payment table
    op.create_table(
        'unit_registration_payment',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('registered_user_id', sa.Integer(), sa.ForeignKey('custom_user.id'), nullable=False, index=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('total_amount', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='paymentproofstatus'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('rejection_note', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('custom_user.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('unit_registration_payment')
    op.drop_column('site_settings', 'payment_qr_url')
    op.execute("DROP TYPE IF EXISTS paymentproofstatus")
