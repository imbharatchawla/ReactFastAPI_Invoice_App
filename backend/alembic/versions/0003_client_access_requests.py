"""add optional client scoped access requests

Revision ID: 0003_client_access
Revises: 0002_access_req_reason
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_client_access"
down_revision = "0002_access_req_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("access_requests", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_access_requests_client_id_clients", "access_requests", "clients", ["client_id"], ["id"])
    op.create_table(
        "user_client_access",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "client_id"),
        sa.UniqueConstraint("user_id", "client_id", name="uq_user_client_access"),
    )


def downgrade() -> None:
    op.drop_table("user_client_access")
    op.drop_constraint("fk_access_requests_client_id_clients", "access_requests", type_="foreignkey")
    op.drop_column("access_requests", "client_id")
