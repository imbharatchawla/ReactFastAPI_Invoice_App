"""make consultant po non unique and add project dates

Revision ID: 0016_po_project_dates
Revises: 0015_consultant_recurring_invoice
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_po_project_dates"
down_revision = "0015_consultant_recurring_invoice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE consultants DROP CONSTRAINT IF EXISTS consultants_po_detail_key")
    op.add_column("projects", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("end_date", sa.Date(), nullable=True))
    op.execute("UPDATE projects SET start_date = DATE '2026-01-01' WHERE start_date IS NULL")
    op.execute("UPDATE projects SET end_date = DATE '2026-12-31' WHERE end_date IS NULL")


def downgrade() -> None:
    op.drop_column("projects", "end_date")
    op.drop_column("projects", "start_date")
    # Recreating the old unique constraint can fail if duplicate PO details were added after upgrade.
    # Keep downgrade non-destructive and do not recreate it automatically.
