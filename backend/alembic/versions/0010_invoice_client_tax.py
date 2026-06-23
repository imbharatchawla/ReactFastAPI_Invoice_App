"""invoice client tax enhancements

Revision ID: 0010_inv_client_tax
Revises: 0009_vendor_po
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_inv_client_tax"
down_revision = "0009_vendor_po"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_clients_bank_account_id", "clients", "bank_accounts", ["bank_account_id"], ["id"])
    op.add_column("invoices", sa.Column("invoice_date", sa.Date(), nullable=True))
    op.execute("UPDATE companies SET gst_percent = 18.00, vat_percent = 0.00 WHERE lower(coalesce(country, '')) = 'india'")


def downgrade() -> None:
    op.drop_column("invoices", "invoice_date")
    op.drop_constraint("fk_clients_bank_account_id", "clients", type_="foreignkey")
    op.drop_column("clients", "bank_account_id")
