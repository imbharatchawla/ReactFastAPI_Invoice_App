"""add consultant currency

Revision ID: 0011_consultant_currency
Revises: 0010_invoice_client_tax
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_consultant_currency"
down_revision = "0010_inv_client_tax"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("consultants", sa.Column("currency", sa.String(length=10), nullable=True, server_default="INR"))

def downgrade():
    op.drop_column("consultants", "currency")
