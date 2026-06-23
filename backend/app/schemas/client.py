from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.client import ClientType
from app.schemas.common import IDModel


class ClientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    client_kind: str = "client"  # client/vendor
    email: EmailStr | None = None
    phone: str | None = None
    countries: list[str] | None = None
    currency: str | None = None
    tax_id: str | None = None
    client_type: ClientType = ClientType.CONTRACT
    details: str | None = None
    billing_address: str | None = None
    notes: str | None = None
    company_id: UUID | None = None
    project_id: UUID | None = None
    milestone_id: UUID | None = None
    bank_account_id: UUID | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    client_kind: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    countries: list[str] | None = None
    currency: str | None = None
    tax_id: str | None = None
    client_type: ClientType | None = None
    details: str | None = None
    billing_address: str | None = None
    notes: str | None = None
    company_id: UUID | None = None
    project_id: UUID | None = None
    milestone_id: UUID | None = None
    bank_account_id: UUID | None = None


class ClientRead(IDModel):
    name: str
    client_kind: str = "client"
    email: EmailStr | None = None
    phone: str | None = None
    country: str | None = None
    countries: list[str] | None = None
    currency: str | None = None
    tax_id: str | None = None
    client_type: str
    details: str | None = None
    billing_address: str | None = None
    notes: str | None = None
    company_id: UUID | None = None
    company_name: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    milestone_id: UUID | None = None
    bank_account_id: UUID | None = None
    milestone_name: str | None = None
    bank_account_id: UUID | None = None
    bank_account_label: str | None = None


class VendorInvoiceRead(IDModel):
    client_id: UUID
    original_filename: str
    stored_filename: str
    content_type: str | None = None
    notes: str | None = None
