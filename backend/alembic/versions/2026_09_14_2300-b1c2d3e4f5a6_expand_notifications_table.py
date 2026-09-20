"""expand_notifications_table

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f7
Create Date: 2026-09-14 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to notifications table
    op.add_column('notifications', sa.Column('severity', sa.String(length=20), server_default='INFO', nullable=False))
    op.add_column('notifications', sa.Column('read_at', sa.DateTime(), nullable=True))
    op.add_column('notifications', sa.Column('related_analysis_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('notifications', sa.Column('related_video_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('notifications', sa.Column('action_url', sa.String(), nullable=True))

    # Add foreign keys (with ON DELETE SET NULL)
    op.create_foreign_key(
        'fk_notifications_related_analysis_id',
        'notifications', 'analysis_results',
        ['related_analysis_id'], ['analysis_id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_notifications_related_video_id',
        'notifications', 'videos',
        ['related_video_id'], ['video_id'],
        ondelete='SET NULL'
    )

    # Add indexes
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_notification_type', 'notifications', ['notification_type'])
    op.create_index('ix_notifications_related_analysis_id', 'notifications', ['related_analysis_id'])
    op.create_index('ix_notifications_related_video_id', 'notifications', ['related_video_id'])
    op.create_index('ix_notifications_user_unread', 'notifications', ['user_id', 'is_read'])
    op.create_index('ix_notifications_dedup', 'notifications', ['user_id', 'notification_type', 'related_analysis_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_dedup', table_name='notifications')
    op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_index('ix_notifications_related_video_id', table_name='notifications')
    op.drop_index('ix_notifications_related_analysis_id', table_name='notifications')
    op.drop_index('ix_notifications_notification_type', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')

    op.drop_constraint('fk_notifications_related_video_id', 'notifications', type_='foreignkey')
    op.drop_constraint('fk_notifications_related_analysis_id', 'notifications', type_='foreignkey')

    op.drop_column('notifications', 'action_url')
    op.drop_column('notifications', 'related_video_id')
    op.drop_column('notifications', 'related_analysis_id')
    op.drop_column('notifications', 'read_at')
    op.drop_column('notifications', 'severity')
