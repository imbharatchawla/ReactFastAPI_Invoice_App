"""add project due days and invoice due date

Revision ID: 0022_due_dates
Revises: 0021_mdoc_bank
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_due_dates"
down_revision = "0021_mdoc_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("due_days", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("invoices", sa.Column("due_date", sa.Date(), nullable=True))
    op.execute("UPDATE invoices SET due_date = invoice_date WHERE due_date IS NULL")


def downgrade() -> None:
    op.drop_column("invoices", "due_date")
    op.drop_column("projects", "due_days")
