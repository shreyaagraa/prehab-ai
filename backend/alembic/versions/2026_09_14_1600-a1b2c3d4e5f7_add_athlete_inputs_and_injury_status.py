"""add_athlete_inputs_and_injury_status

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-09-14 16:00:00.000000

"""
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('athletes', sa.Column('dominant_leg', sa.String(), nullable=True))
    op.add_column('athletes', sa.Column('training_sessions_per_week', sa.Integer(), nullable=True))
    op.add_column('athletes', sa.Column('average_session_duration', sa.Integer(), nullable=True))
    op.add_column('athletes', sa.Column('average_session_rpe', sa.Float(), nullable=True))
    op.add_column('athletes', sa.Column('weekly_training_load', sa.Float(), nullable=True))
    op.add_column('athletes', sa.Column('current_fatigue_level', sa.Integer(), nullable=True))
    op.add_column('athletes', sa.Column('has_injury_history', sa.String(), nullable=True))

    op.add_column('injury_history', sa.Column('status', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('injury_history', 'status')

    op.drop_column('athletes', 'has_injury_history')
    op.drop_column('athletes', 'current_fatigue_level')
    op.drop_column('athletes', 'weekly_training_load')
    op.drop_column('athletes', 'average_session_rpe')
    op.drop_column('athletes', 'average_session_duration')
    op.drop_column('athletes', 'training_sessions_per_week')
    op.drop_column('athletes', 'dominant_leg')
