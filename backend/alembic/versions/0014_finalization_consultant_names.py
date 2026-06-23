"""add invoice finalization requests and consultant first last names

Revision ID: 0014_finalize_names
Revises: 0013_invoice_update_audit
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_finalize_names"
down_revision = "0013_invoice_update_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultants", sa.Column("first_name", sa.String(length=120), nullable=True))
    op.add_column("consultants", sa.Column("last_name", sa.String(length=120), nullable=True))
    op.execute("""
        UPDATE consultants
        SET first_name = split_part(name, ' ', 1),
            last_name = NULLIF(trim(substr(name, length(split_part(name, ' ', 1)) + 1)), '')
        WHERE first_name IS NULL
    """)

    op.create_table(
        "invoice_finalization_requests",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_finalization_requests_invoice_id"), "invoice_finalization_requests", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_invoice_finalization_requests_requester_id"), "invoice_finalization_requests", ["requester_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_finalization_requests_requester_id"), table_name="invoice_finalization_requests")
    op.drop_index(op.f("ix_invoice_finalization_requests_invoice_id"), table_name="invoice_finalization_requests")
    op.drop_table("invoice_finalization_requests")
    op.drop_column("consultants", "last_name")
    op.drop_column("consultants", "first_name")
