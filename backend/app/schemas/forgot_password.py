from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.common import IDModel


class ForgotPasswordCreate(BaseModel):
    email: EmailStr


class ForgotPasswordDecision(BaseModel):
    action: str


class ForgotPasswordRead(IDModel):
    user_id: UUID
    email: str
    requester_name: str | None = None
    status: str
    decided_by_id: UUID | None = None


class ForgotPasswordRecoverResponse(BaseModel):
    id: UUID
    email: str
    status: str
    temporary_password: str
