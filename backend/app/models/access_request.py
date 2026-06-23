from enum import Enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AccessRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(UUIDMixin, TimestampMixin, Base):
    """HR or any user can request access to a module. Admin/superadmin can approve."""

    __tablename__ = "access_requests"

    requester_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    module_code: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_permission: Mapped[str] = mapped_column(String(20), nullable=False, default="create")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional client scope. Useful when HR requests invoice access for one approved client.
    client_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AccessRequestStatus.PENDING.value)
    decided_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Reason supplied by admin/superadmin when rejecting a request.
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
