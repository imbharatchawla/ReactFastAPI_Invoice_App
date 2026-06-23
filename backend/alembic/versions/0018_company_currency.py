"""add company currency

Revision ID: 0018_company_currency
Revises: 0017_invoice_status_targets
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_company_currency"
down_revision = "0017_invoice_status_targets"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("currency", sa.String(length=10), nullable=True, server_default="INR"))
    op.execute("UPDATE companies SET currency = 'INR' WHERE currency IS NULL")
    op.alter_column("companies", "currency", server_default=None)


def downgrade():
    op.drop_column("companies", "currency")
