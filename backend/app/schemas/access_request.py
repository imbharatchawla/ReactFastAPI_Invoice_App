from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import IDModel


class AccessRequestCreate(BaseModel):
    module_code: str
    requested_permission: str = "create"
    reason: str = Field(min_length=2)
    # Optional. For HR invoice access, provide the client ID they should be allowed to invoice.
    client_id: UUID | None = None


class AccessRequestRead(IDModel):
    requester_id: UUID
    requester_email: str | None = None
    requester_name: str | None = None
    module_code: str
    requested_permission: str
    reason: str = ""
    client_id: UUID | None = None
    status: str
    decided_by_id: UUID | None = None
    rejection_reason: str | None = None


class AccessDecision(BaseModel):
    status: str  # approved/rejected
    rejection_reason: str | None = None
