"""add_google_sub_to_users

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-14 13:00:00.000000

"""
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'google_sub',
            sa.String(),
            nullable=True,
        )
    )
    op.create_index(
        op.f('ix_users_google_sub'),
        'users',
        ['google_sub'],
        unique=True,
    )
    op.alter_column(
        'users',
        'password',
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'users',
        'password',
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'google_sub')
