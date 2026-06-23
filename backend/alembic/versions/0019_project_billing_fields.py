"""add project billing fields

Revision ID: 0019_project_billing_fields
Revises: 0018_company_currency
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0019_project_billing_fields"
down_revision = "0018_company_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("billing_rate", sa.Numeric(12, 2), nullable=True, server_default="0.00"))
    op.add_column("projects", sa.Column("billing_unit", sa.String(length=30), nullable=True, server_default="hours"))
    op.execute("UPDATE projects SET billing_rate = 0.00 WHERE billing_rate IS NULL")
    op.execute("UPDATE projects SET billing_unit = 'hours' WHERE billing_unit IS NULL")
    op.alter_column("projects", "billing_rate", server_default=None)
    op.alter_column("projects", "billing_unit", server_default=None)


def downgrade() -> None:
    op.drop_column("projects", "billing_unit")
    op.drop_column("projects", "billing_rate")
