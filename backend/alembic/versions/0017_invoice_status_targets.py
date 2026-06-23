"""add invoice status target approvals

Revision ID: 0017_invoice_status_targets
Revises: 0016_po_project_dates
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_invoice_status_targets"
down_revision = "0016_po_project_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoice_finalization_requests", sa.Column("target_status", sa.String(length=50), nullable=False, server_default="issued"))
    op.execute("UPDATE invoices SET status = 'issued' WHERE status = 'final'")
    op.execute("UPDATE invoice_finalization_requests SET target_status = 'issued' WHERE target_status IS NULL OR target_status = 'final'")
    op.alter_column("invoice_finalization_requests", "target_status", server_default=None)


def downgrade() -> None:
    op.execute("UPDATE invoices SET status = 'final' WHERE status = 'issued'")
    op.drop_column("invoice_finalization_requests", "target_status")
