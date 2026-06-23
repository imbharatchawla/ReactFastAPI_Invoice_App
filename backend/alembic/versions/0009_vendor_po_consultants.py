"""add vendor upload records plus project PO and consultant dates

Revision ID: 0009_vendor_po
Revises: 0008_invoice_details
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_vendor_po"
down_revision = "0008_invoice_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("client_kind", sa.String(length=20), nullable=False, server_default="client"))
    op.add_column("projects", sa.Column("po_number", sa.String(length=255), nullable=True))
    op.add_column("consultants", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("consultants", sa.Column("end_date", sa.Date(), nullable=True))
    op.create_table(
        "vendor_invoices",
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("vendor_invoices")
    op.drop_column("consultants", "end_date")
    op.drop_column("consultants", "start_date")
    op.drop_column("projects", "po_number")
    op.drop_column("clients", "client_kind")
