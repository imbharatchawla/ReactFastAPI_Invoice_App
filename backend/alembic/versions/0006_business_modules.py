"""add business modules and improved client/company mappings

Revision ID: 0006_business
Revises: 0005_invoice_gen
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_business"
down_revision = "0005_invoice_gen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("vat_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("companies", sa.Column("gst_percent", sa.Numeric(5, 2), nullable=True))
    op.execute("UPDATE companies SET vat_percent = 23.00 WHERE vat_percent IS NULL")
    op.execute("UPDATE companies SET gst_percent = 18.00 WHERE gst_percent IS NULL")

    op.add_column("clients", sa.Column("countries", sa.Text(), nullable=True))
    op.add_column("clients", sa.Column("currency", sa.String(10), nullable=True))
    op.add_column("clients", sa.Column("details", sa.Text(), nullable=True))
    op.execute("UPDATE clients SET countries = country WHERE country IS NOT NULL AND countries IS NULL")

    op.add_column("projects", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_projects_client_id_clients", "projects", "clients", ["client_id"], ["id"])

    op.create_table(
        "consultants",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("billing_type", sa.String(50), nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("po_detail", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("po_detail"),
    )
    op.create_index(op.f("ix_consultants_name"), "consultants", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_consultants_name"), table_name="consultants")
    op.drop_table("consultants")
    op.drop_constraint("fk_projects_client_id_clients", "projects", type_="foreignkey")
    op.drop_column("projects", "client_id")
    op.drop_column("clients", "details")
    op.drop_column("clients", "currency")
    op.drop_column("clients", "countries")
    op.drop_column("companies", "gst_percent")
    op.drop_column("companies", "vat_percent")
