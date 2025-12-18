"""add_site_settings_notices_quicklinks

Revision ID: a076b7859c09
Revises: 71c337eb431c
Create Date: 2024-12-17

This migration adds three new tables for site settings management:
- site_settings: Singleton table for site-wide configuration
- notices: Marquee notices for homepage
- quick_links: Quick navigation links for homepage
"""

revision = 'a076b7859c09'
down_revision = '71c337eb431c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Create site_settings table
    op.create_table('site_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_name', sa.String(length=255), nullable=False),
        sa.Column('app_subtitle', sa.String(length=255), nullable=True),
        sa.Column('about_text', sa.Text(), nullable=True),
        sa.Column('logo_primary_url', sa.String(length=500), nullable=True),
        sa.Column('logo_secondary_url', sa.String(length=500), nullable=True),
        sa.Column('logo_tertiary_url', sa.String(length=500), nullable=True),
        sa.Column('registration_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('registration_closed_message', sa.String(length=255), nullable=True),
        sa.Column('contact_address', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('social_facebook', sa.String(length=500), nullable=True),
        sa.Column('social_instagram', sa.String(length=500), nullable=True),
        sa.Column('social_youtube', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create notices table
    op.create_table('notices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='normal'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notices_id'), 'notices', ['id'], unique=False)

    # Create quick_links table
    op.create_table('quick_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quick_links_id'), 'quick_links', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_quick_links_id'), table_name='quick_links')
    op.drop_table('quick_links')
    op.drop_index(op.f('ix_notices_id'), table_name='notices')
    op.drop_table('notices')
    op.drop_table('site_settings')
