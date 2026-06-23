"""add consultant recurring invoice flag

Revision ID: 0015_consultant_recurring_invoice
Revises: 0014_finalize_names
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_consultant_recurring_invoice"
down_revision = "0014_finalize_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultants", sa.Column("is_recurring_invoice", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("consultants", "is_recurring_invoice", server_default=None)


def downgrade() -> None:
    op.drop_column("consultants", "is_recurring_invoice")
