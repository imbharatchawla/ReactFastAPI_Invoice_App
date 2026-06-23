"""add companies projects milestones and client mappings

Revision ID: 0004_catalog_map
Revises: 0003_client_access
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_catalog_map"
down_revision = "0003_client_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("tax_id", sa.String(100), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=False)

    op.create_table(
        "projects",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_detail", sa.Text(), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)

    op.create_table(
        "milestones",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_milestones_name"), "milestones", ["name"], unique=False)

    op.add_column("clients", sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("clients", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("clients", sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_clients_company_id_companies", "clients", "companies", ["company_id"], ["id"])
    op.create_foreign_key("fk_clients_project_id_projects", "clients", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_clients_milestone_id_milestones", "clients", "milestones", ["milestone_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_clients_milestone_id_milestones", "clients", type_="foreignkey")
    op.drop_constraint("fk_clients_project_id_projects", "clients", type_="foreignkey")
    op.drop_constraint("fk_clients_company_id_companies", "clients", type_="foreignkey")
    op.drop_column("clients", "milestone_id")
    op.drop_column("clients", "project_id")
    op.drop_column("clients", "company_id")
    op.drop_index(op.f("ix_milestones_name"), table_name="milestones")
    op.drop_table("milestones")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_table("companies")
