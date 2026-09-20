"""add_title_to_videos

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-11 17:10:00.000000

"""
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'videos',
        sa.Column(
            'title',
            sa.String(length=255),
            nullable=True,
        )
    )


def downgrade() -> None:
    op.drop_column('videos', 'title')
