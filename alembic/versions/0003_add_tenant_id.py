"""add tenant_id columns

Revision ID: 0003_add_tenant_id
Revises: 0002_add_user_role
Create Date: 2026-08-16 10:22:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_add_tenant_id"
down_revision: str | None = "0002_add_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.add_column(
        "approval_requests",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_approval_requests_tenant_id", "approval_requests", ["tenant_id"], unique=False)
    op.add_column(
        "approval_requests",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approval_requests", "user_id")
    op.drop_index("ix_approval_requests_tenant_id", table_name="approval_requests")
    op.drop_column("approval_requests", "tenant_id")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")