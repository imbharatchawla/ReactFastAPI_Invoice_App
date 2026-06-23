"""add rejection reason to access requests

Revision ID: 0002_access_req_reason
Revises: 0001_initial
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_access_req_reason"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("access_requests", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("access_requests", "rejection_reason")
