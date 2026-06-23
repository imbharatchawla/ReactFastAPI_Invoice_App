"""add forgot password requests

Revision ID: 0023_forgot_pwd
Revises: 0022_due_dates
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_forgot_pwd"
down_revision = "0022_due_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forgot_password_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forgot_password_requests_email", "forgot_password_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_forgot_password_requests_email", table_name="forgot_password_requests")
    op.drop_table("forgot_password_requests")
