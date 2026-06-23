from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModuleDocument(UUIDMixin, TimestampMixin, Base):
    """Generic uploaded document attached to any module record."""

    __tablename__ = "module_documents"

    module_code: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    record_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(700), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
