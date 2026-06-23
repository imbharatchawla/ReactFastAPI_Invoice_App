"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("email", sa.String(255), nullable=False), sa.Column("full_name", sa.String(255), nullable=False), sa.Column("hashed_password", sa.String(500), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("is_superadmin", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table("roles", sa.Column("name", sa.String(100), nullable=False), sa.Column("description", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)
    op.create_table("modules", sa.Column("code", sa.String(50), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_modules_code"), "modules", ["code"], unique=True)
    op.create_table("clients", sa.Column("name", sa.String(255), nullable=False), sa.Column("email", sa.String(255), nullable=True), sa.Column("phone", sa.String(50), nullable=True), sa.Column("country", sa.String(100), nullable=True), sa.Column("tax_id", sa.String(100), nullable=True), sa.Column("client_type", sa.String(50), nullable=False), sa.Column("billing_address", sa.Text(), nullable=True), sa.Column("notes", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_clients_name"), "clients", ["name"], unique=False)
    op.create_table("bank_accounts", sa.Column("account_holder_name", sa.String(255), nullable=False), sa.Column("bank_name", sa.String(255), nullable=False), sa.Column("account_number", sa.String(100), nullable=False), sa.Column("country", sa.String(100), nullable=False), sa.Column("currency", sa.String(10), nullable=False), sa.Column("ifsc_code", sa.String(50), nullable=True), sa.Column("swift_code", sa.String(50), nullable=True), sa.Column("iban", sa.String(100), nullable=True), sa.Column("routing_number", sa.String(100), nullable=True), sa.Column("branch_address", sa.Text(), nullable=True), sa.Column("notes", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_table("user_roles", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False), sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("user_id", "role_id"), sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"))
    op.create_table("role_module_permissions", sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("can_read", sa.Boolean(), nullable=False), sa.Column("can_create", sa.Boolean(), nullable=False), sa.Column("can_update", sa.Boolean(), nullable=False), sa.Column("can_delete", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("role_id", "module_id", name="uq_role_module_permission"))
    op.create_table("access_requests", sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("module_code", sa.String(50), nullable=False), sa.Column("requested_permission", sa.String(20), nullable=False), sa.Column("reason", sa.Text(), nullable=True), sa.Column("status", sa.String(20), nullable=False), sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]), sa.ForeignKeyConstraint(["requester_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("invoices", sa.Column("invoice_number", sa.String(100), nullable=False), sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("invoice_format", sa.String(50), nullable=False), sa.Column("status", sa.String(50), nullable=False), sa.Column("currency", sa.String(10), nullable=False), sa.Column("subtotal", sa.Numeric(12, 2), nullable=False), sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False), sa.Column("total_amount", sa.Numeric(12, 2), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]), sa.ForeignKeyConstraint(["client_id"], ["clients.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=True)


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("access_requests")
    op.drop_table("role_module_permissions")
    op.drop_table("user_roles")
    op.drop_table("bank_accounts")
    op.drop_table("clients")
    op.drop_index(op.f("ix_modules_code"), table_name="modules")
    op.drop_table("modules")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
