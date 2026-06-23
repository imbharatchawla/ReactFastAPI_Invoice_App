"""add invoice update audit

Revision ID: 0013_invoice_update_audit
Revises: 0012_revert_requests
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_invoice_update_audit"
down_revision = "0012_revert_requests"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("invoices", sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_invoices_updated_by_user_id_users", "invoices", "users", ["updated_by_user_id"], ["id"])


def downgrade():
    op.drop_constraint("fk_invoices_updated_by_user_id_users", "invoices", type_="foreignkey")
    op.drop_column("invoices", "updated_by_user_id")
