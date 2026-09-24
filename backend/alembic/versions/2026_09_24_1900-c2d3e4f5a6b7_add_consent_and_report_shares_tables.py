"""add_consent_and_report_shares_tables

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-09-24 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add date_of_birth to users table
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))

    # 2. Create consent_records table
    op.create_table(
        'consent_records',
        sa.Column('consent_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.athlete_id', ondelete='CASCADE'), nullable=True),
        sa.Column('purpose', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='GRANTED', nullable=False),
        sa.Column('notice_version', sa.String(length=20), server_default='v1.0', nullable=False),
        sa.Column('provided_by', sa.String(length=30), server_default='self', nullable=False),
        sa.Column('guardian_name', sa.String(length=255), nullable=True),
        sa.Column('guardian_email', sa.String(length=255), nullable=True),
        sa.Column('guardian_relationship', sa.String(length=50), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_consent_records_user_id', 'consent_records', ['user_id'])
    op.create_index('ix_consent_records_athlete_id', 'consent_records', ['athlete_id'])
    op.create_index('ix_consent_records_purpose', 'consent_records', ['purpose'])
    op.create_index('ix_consent_records_status', 'consent_records', ['status'])

    # 3. Create report_shares table
    op.create_table(
        'report_shares',
        sa.Column('share_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('athletes.athlete_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_role', sa.String(length=50), nullable=False),
        sa.Column('is_authorized', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('athlete_id', 'target_role', name='uq_report_shares_athlete_role'),
    )
    op.create_index('ix_report_shares_athlete_id', 'report_shares', ['athlete_id'])
    op.create_index('ix_report_shares_user_id', 'report_shares', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_report_shares_user_id', table_name='report_shares')
    op.drop_index('ix_report_shares_athlete_id', table_name='report_shares')
    op.drop_table('report_shares')

    op.drop_index('ix_consent_records_status', table_name='consent_records')
    op.drop_index('ix_consent_records_purpose', table_name='consent_records')
    op.drop_index('ix_consent_records_athlete_id', table_name='consent_records')
    op.drop_index('ix_consent_records_user_id', table_name='consent_records')
    op.drop_table('consent_records')

    op.drop_column('users', 'date_of_birth')
