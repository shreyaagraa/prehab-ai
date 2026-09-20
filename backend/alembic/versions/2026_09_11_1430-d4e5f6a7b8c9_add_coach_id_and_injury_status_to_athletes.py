"""add_coach_id_and_injury_status_to_athletes

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-11 14:30:00.000000

"""
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'athletes',
        sa.Column(
            'coach_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.user_id'),
            nullable=True,
        )
    )
    op.add_column(
        'athletes',
        sa.Column(
            'injury_status',
            sa.String(),
            nullable=True,
            server_default='Healthy',
        )
    )


def downgrade() -> None:
    op.drop_column('athletes', 'injury_status')
    op.drop_column('athletes', 'coach_id')
