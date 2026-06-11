"""Add valid_until, OTPLogs, and Channel Settings fields

Revision ID: 001_add_new_models
Revises: 
Create Date: 2026-06-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '001_add_new_models'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add valid_until to user_service_assignments
    op.add_column('user_service_assignments', sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True))
    
    # Add channel_url and emoji to channel_settings
    op.add_column('channel_settings', sa.Column('channel_url', sa.String(length=500), nullable=True))
    op.add_column('channel_settings', sa.Column('emoji', sa.String(length=10), server_default='📢'))
    
    # Create otp_logs table
    op.create_table('otp_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('otp_value', sa.String(length=50), nullable=False),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_otp_logs_viewed_at'), 'otp_logs', ['viewed_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_otp_logs_viewed_at'), table_name='otp_logs')
    op.drop_table('otp_logs')
    op.drop_column('channel_settings', 'emoji')
    op.drop_column('channel_settings', 'channel_url')
    op.drop_column('user_service_assignments', 'valid_until')
