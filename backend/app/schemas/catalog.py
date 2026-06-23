from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import IDModel


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    address: str | None = None
    country: str | None = None
    tax_id: str | None = None
    currency: str | None = "INR"
    vat_percent: Decimal | None = Decimal("23.00")
    gst_percent: Decimal | None = Decimal("18.00")
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    bank_account_ids: list[UUID] | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    country: str | None = None
    tax_id: str | None = None
    currency: str | None = None
    vat_percent: Decimal | None = None
    gst_percent: Decimal | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    bank_account_ids: list[UUID] | None = None


class CompanyRead(IDModel):
    name: str
    address: str | None = None
    country: str | None = None
    tax_id: str | None = None
    currency: str | None = None
    vat_percent: Decimal | None = None
    gst_percent: Decimal | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    notes: str | None = None
    bank_account_ids: list[UUID] = []
    bank_account_labels: list[str] = []


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_detail: str | None = None
    client_id: UUID | None = None
    company_id: UUID | None = None
    po_number: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_rate: Decimal | None = Decimal("0.00")
    billing_unit: str | None = "hours"
    currency: str | None = "INR"
    due_days: int | None = 0


class ProjectUpdate(BaseModel):
    name: str | None = None
    project_detail: str | None = None
    client_id: UUID | None = None
    company_id: UUID | None = None
    po_number: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_rate: Decimal | None = None
    billing_unit: str | None = None
    currency: str | None = None
    due_days: int | None = None


class ProjectRead(IDModel):
    name: str
    project_detail: str | None = None
    client_id: UUID | None = None
    client_name: str | None = None
    company_id: UUID | None = None
    company_name: str | None = None
    po_number: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_rate: Decimal | None = None
    billing_unit: str | None = None
    currency: str | None = None
    due_days: int | None = None


class MilestoneCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_id: UUID
    details: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class MilestoneUpdate(BaseModel):
    name: str | None = None
    project_id: UUID | None = None
    details: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class MilestoneRead(IDModel):
    name: str
    project_id: UUID
    project_name: str | None = None
    client_name: str | None = None
    details: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ConsultantCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    name: str | None = None
    billing_type: str = "monthly"
    currency: str | None = "INR"
    rate: Decimal = Decimal("0.00")
    project_id: UUID | None = None
    po_detail: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    is_recurring_invoice: bool = False


class ConsultantUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    billing_type: str | None = None
    currency: str | None = None
    rate: Decimal | None = None
    project_id: UUID | None = None
    po_detail: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    is_recurring_invoice: bool | None = None


class ConsultantRead(IDModel):
    name: str
    first_name: str | None = None
    last_name: str | None = None
    billing_type: str
    currency: str | None = None
    rate: Decimal
    project_id: UUID | None = None
    project_name: str | None = None
    client_name: str | None = None
    po_detail: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    is_recurring_invoice: bool = False
