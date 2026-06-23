"""normalize company tax defaults

Revision ID: 0007_tax_actions
Revises: 0006_business
Create Date: 2026-05-02
"""
from alembic import op

revision = "0007_tax_actions"
down_revision = "0006_business"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Business rule:
    # - India companies use GST 23% and VAT 0%
    # - All other countries use VAT 23% and GST 0%
    op.execute("""
        UPDATE companies
        SET vat_percent = 0.00,
            gst_percent = 23.00
        WHERE LOWER(TRIM(COALESCE(country, ''))) = 'india'
    """)
    op.execute("""
        UPDATE companies
        SET vat_percent = 23.00,
            gst_percent = 0.00
        WHERE LOWER(TRIM(COALESCE(country, ''))) <> 'india'
           OR country IS NULL
    """)


def downgrade() -> None:
    # Keep schema unchanged; restore previous broad default values where possible.
    op.execute("UPDATE companies SET vat_percent = 23.00 WHERE vat_percent IS NULL")
    op.execute("UPDATE companies SET gst_percent = 18.00 WHERE gst_percent IS NULL")
