"""add project currency

Revision ID: 0020_project_currency
Revises: 0019_project_billing_fields
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_project_currency"
down_revision = "0019_project_billing_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("currency", sa.String(length=10), nullable=True, server_default="INR"))
    op.execute("UPDATE projects SET currency = 'INR' WHERE currency IS NULL")


def downgrade() -> None:
    op.drop_column("projects", "currency")
