"""add user role column

Revision ID: 0002_add_user_role
Revises: 0001_initial_schema
Create Date: 2026-08-13 21:42:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_user_role"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
