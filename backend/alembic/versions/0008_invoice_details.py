"""add detailed invoice fields

Revision ID: 0008_invoice_details
Revises: 0007_tax_actions
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_invoice_details"
down_revision = "0007_tax_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("billing_type", sa.String(length=50), nullable=True))
    op.add_column("invoices", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("hours", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("rate", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("fee_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("tax_label", sa.String(length=20), nullable=True))
    op.add_column("invoices", sa.Column("tax_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("invoices", sa.Column("expense_total", sa.Numeric(12, 2), nullable=True, server_default="0"))
    op.add_column("invoices", sa.Column("expenses_json", sa.Text(), nullable=True))
    op.create_foreign_key("fk_invoices_project_id_projects", "invoices", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_invoices_milestone_id_milestones", "invoices", "milestones", ["milestone_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_invoices_milestone_id_milestones", "invoices", type_="foreignkey")
    op.drop_constraint("fk_invoices_project_id_projects", "invoices", type_="foreignkey")
    op.drop_column("invoices", "expenses_json")
    op.drop_column("invoices", "expense_total")
    op.drop_column("invoices", "tax_percent")
    op.drop_column("invoices", "tax_label")
    op.drop_column("invoices", "fee_amount")
    op.drop_column("invoices", "rate")
    op.drop_column("invoices", "hours")
    op.drop_column("invoices", "milestone_id")
    op.drop_column("invoices", "project_id")
    op.drop_column("invoices", "billing_type")
