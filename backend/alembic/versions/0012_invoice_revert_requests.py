"""add invoice revert requests

Revision ID: 0012_revert_requests
Revises: 0011_consultant_currency
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_revert_requests"
down_revision = "0011_consultant_currency"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoice_revert_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_revert_requests_invoice_id", "invoice_revert_requests", ["invoice_id"])
    op.create_index("ix_invoice_revert_requests_requester_id", "invoice_revert_requests", ["requester_id"])


def downgrade():
    op.drop_index("ix_invoice_revert_requests_requester_id", table_name="invoice_revert_requests")
    op.drop_index("ix_invoice_revert_requests_invoice_id", table_name="invoice_revert_requests")
    op.drop_table("invoice_revert_requests")
