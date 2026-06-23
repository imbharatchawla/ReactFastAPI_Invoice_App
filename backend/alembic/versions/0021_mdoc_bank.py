"""add milestone dates company bank links and module documents

Revision ID: 0021_mdoc_bank
Revises: 0020_project_currency
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021_mdoc_bank"
down_revision = "0020_project_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("milestones", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("milestones", sa.Column("end_date", sa.Date(), nullable=True))
    op.create_table(
        "company_bank_accounts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "module_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("module_code", sa.String(length=60), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=700), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_module_documents_module_code", "module_documents", ["module_code"])
    op.create_index("ix_module_documents_record_id", "module_documents", ["record_id"])


def downgrade() -> None:
    op.drop_index("ix_module_documents_record_id", table_name="module_documents")
    op.drop_index("ix_module_documents_module_code", table_name="module_documents")
    op.drop_table("module_documents")
    op.drop_table("company_bank_accounts")
    op.drop_column("milestones", "end_date")
    op.drop_column("milestones", "start_date")
