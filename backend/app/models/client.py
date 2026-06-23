from enum import Enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ClientType(str, Enum):
    CONTRACT = "contract"
    MILESTONE = "milestone"
    PERMANENT = "permanent"


class Client(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)  # legacy single country
    countries: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_type: Mapped[str] = mapped_column(String(50), nullable=False, default=ClientType.CONTRACT.value)
    client_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="client")  # client/vendor
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    company_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    milestone_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    bank_account_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=True)

    company = relationship("Company")
    project = relationship("Project", foreign_keys=[project_id])
    milestone = relationship("Milestone")
    bank_account = relationship("BankAccount")
    projects = relationship("Project", back_populates="client", foreign_keys="Project.client_id")
    vendor_invoices = relationship("VendorInvoice", back_populates="client", cascade="all, delete-orphan")


class VendorInvoice(UUIDMixin, TimestampMixin, Base):
    """Uploaded vendor invoice record. File is stored locally under backend/uploads."""

    __tablename__ = "vendor_invoices"

    client_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    client = relationship("Client", back_populates="vendor_invoices")
