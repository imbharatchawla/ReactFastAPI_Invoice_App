from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class BankAccount(UUIDMixin, TimestampMixin, Base):
    """Flexible bank details for Indian and foreign accounts."""

    __tablename__ = "bank_accounts"

    account_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    ifsc_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    swift_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(100), nullable=True)
    routing_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    branch_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
