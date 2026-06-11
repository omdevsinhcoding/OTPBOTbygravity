"""architecture_refactor

Revision ID: 002
Revises: 001
Create Date: 2026-06-11 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # AdminUser permissions
    op.add_column('admin_users', sa.Column('permissions', postgresql.ARRAY(sa.String()), nullable=True))
    
    # ChannelSetting visibility flags
    op.add_column('channel_settings', sa.Column('show_in_keyboard', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('channel_settings', sa.Column('show_in_inline', sa.Boolean(), server_default='true', nullable=False))
    
    # OTPLog expires_at
    op.add_column('otp_logs', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    
    # UserServiceAssignment enhancements
    op.add_column('user_service_assignments', sa.Column('service_name_snapshot', sa.String(length=100), nullable=True))
    op.add_column('user_service_assignments', sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_service_assignments', sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('user_service_assignments', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # AdminUser permissions
    op.drop_column('admin_users', 'permissions')
    
    # ChannelSetting visibility flags
    op.drop_column('channel_settings', 'show_in_inline')
    op.drop_column('channel_settings', 'show_in_keyboard')
    
    # OTPLog expires_at
    op.drop_column('otp_logs', 'expires_at')
    
    # UserServiceAssignment enhancements
    op.drop_column('user_service_assignments', 'notes')
    op.drop_column('user_service_assignments', 'expired_at')
    op.drop_column('user_service_assignments', 'activated_at')
    op.drop_column('user_service_assignments', 'service_name_snapshot')
