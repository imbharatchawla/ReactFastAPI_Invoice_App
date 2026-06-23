from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Table, Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

company_bank_accounts = Table(
    "company_bank_accounts",
    Base.metadata,
    Column("company_id", UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
    Column("bank_account_id", UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), primary_key=True),
)


class Company(UUIDMixin, TimestampMixin, Base):
    """Company/master entity. VAT/GST percentages are stored separately for regional invoices."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, default="INR")
    vat_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, default=Decimal("23.00"))
    gst_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, default=Decimal("18.00"))
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    bank_accounts = relationship("BankAccount", secondary=company_bank_accounts)


class Project(UUIDMixin, TimestampMixin, Base):
    """Project details. A project belongs to a client and can have milestones/consultants."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    project_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)  # legacy
    client_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=Decimal("0.00"))
    billing_unit: Mapped[str | None] = mapped_column(String(30), nullable=True, default="hours")
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, default="INR")
    due_days: Mapped[int | None] = mapped_column(nullable=True, default=0)

    company = relationship("Company")
    client = relationship("Client", back_populates="projects", foreign_keys=[client_id])
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    consultants = relationship("Consultant", back_populates="project")


class Milestone(UUIDMixin, TimestampMixin, Base):
    """Milestone mapped to a project."""

    __tablename__ = "milestones"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    project_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    project = relationship("Project", back_populates="milestones")


class Consultant(UUIDMixin, TimestampMixin, Base):
    """Consultant mapped to a project with PO and billing information."""

    __tablename__ = "consultants"

    # name is kept for backward compatibility and stores "First Last".
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    billing_type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True, default="INR")
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    project_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    po_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project = relationship("Project", back_populates="consultants")
