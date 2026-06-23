from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    PENDING_FINAL = "pending_final"



class InvoiceFormat(str, Enum):
    PROJECT = "project"
    MILESTONE = "milestone"
    STAFFING = "staffing"


class Invoice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    invoice_date: Mapped[date | None] = mapped_column(nullable=True)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    client_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    bank_account_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=True)
    generated_by_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invoice_format: Mapped[str] = mapped_column(String(50), nullable=False, default=InvoiceFormat.STAFFING.value)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=InvoiceStatus.DRAFT.value)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    # Detailed invoice form fields. These are nullable so older invoices remain valid.
    billing_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    milestone_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    expense_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    expenses_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    generated_by = relationship("User", foreign_keys=[generated_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
    client = relationship("Client")
    project = relationship("Project")
    milestone = relationship("Milestone")


class InvoiceFinalizationRequest(UUIDMixin, TimestampMixin, Base):
    """Request raised by a non-admin user to make an invoice final."""

    __tablename__ = "invoice_finalization_requests"

    invoice_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_status: Mapped[str] = mapped_column(String(50), nullable=False, default="issued")

    invoice = relationship("Invoice")
    requester = relationship("User", foreign_keys=[requester_id])
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])


class InvoiceRevertRequest(UUIDMixin, TimestampMixin, Base):
    """Request raised by a non-admin user to move an issued/payment invoice back to draft."""

    __tablename__ = "invoice_revert_requests"

    invoice_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    invoice = relationship("Invoice")
    requester = relationship("User", foreign_keys=[requester_id])
    decided_by = relationship("User", foreign_keys=[decided_by_user_id])
