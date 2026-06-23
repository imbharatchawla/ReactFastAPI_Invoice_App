from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.invoice import InvoiceFormat, InvoiceStatus
from app.schemas.bank import BankAccountRead
from app.schemas.common import IDModel


class InvoiceCreate(BaseModel):
    invoice_number: str | None = Field(default=None, min_length=3)
    invoice_date: date | None = None
    due_date: date | None = None
    client_id: UUID
    bank_account_id: UUID | None = None
    invoice_format: InvoiceFormat = InvoiceFormat.STAFFING
    status: InvoiceStatus = InvoiceStatus.DRAFT
    currency: str = "INR"
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    billing_type: str | None = None
    project_id: UUID | None = None
    milestone_id: UUID | None = None
    hours: Decimal | None = None
    rate: Decimal | None = None
    fee_amount: Decimal | None = None
    tax_label: str | None = None
    tax_percent: Decimal | None = None
    expense_total: Decimal | None = Decimal("0.00")
    expenses_json: str | None = None
    description: str | None = None


class InvoiceUpdate(BaseModel):
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    client_id: UUID | None = None
    bank_account_id: UUID | None = None
    invoice_format: InvoiceFormat | None = None
    status: InvoiceStatus | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    billing_type: str | None = None
    project_id: UUID | None = None
    milestone_id: UUID | None = None
    hours: Decimal | None = None
    rate: Decimal | None = None
    fee_amount: Decimal | None = None
    tax_label: str | None = None
    tax_percent: Decimal | None = None
    expense_total: Decimal | None = None
    expenses_json: str | None = None
    description: str | None = None


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


class InvoiceFinalizationRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
    target_status: str | None = None


class InvoiceFinalizationRequestDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    rejection_reason: str | None = None

class InvoiceRead(IDModel):
    invoice_number: str
    invoice_date: date | None = None
    due_date: date | None = None
    client_id: UUID
    bank_account_id: UUID | None = None
    bank_details: BankAccountRead | None = None
    generated_by_user_id: UUID | None = None
    generated_by_name: str | None = None
    generated_by_email: str | None = None
    invoice_format: str
    status: str
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    billing_type: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    milestone_id: UUID | None = None
    milestone_name: str | None = None
    hours: Decimal | None = None
    rate: Decimal | None = None
    fee_amount: Decimal | None = None
    tax_label: str | None = None
    tax_percent: Decimal | None = None
    expense_total: Decimal | None = None
    expenses_json: str | None = None
    description: str | None = None
    updated_by_user_id: UUID | None = None
    updated_by_name: str | None = None
    updated_by_email: str | None = None
    updated_on: datetime | None = None




class BulkRecurringInvoiceCreate(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    status: InvoiceStatus = InvoiceStatus.DRAFT


class BulkRecurringInvoiceResult(BaseModel):
    created_count: int
    skipped_count: int
    created: list[InvoiceRead] = []
    skipped: list[str] = []


class InvoiceRevertRequestCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class InvoiceRevertRequestDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    rejection_reason: str | None = None


class InvoiceFinalizationRequestRead(IDModel):
    invoice_id: UUID
    invoice_number: str | None = None
    target_status: str = "issued"
    requester_id: UUID
    requester_name: str | None = None
    requester_email: str | None = None
    status: str
    reason: str | None = None
    rejection_reason: str | None = None
    decided_by_user_id: UUID | None = None


class InvoiceRevertRequestRead(IDModel):
    invoice_id: UUID
    invoice_number: str | None = None
    requester_id: UUID
    requester_name: str | None = None
    requester_email: str | None = None
    status: str
    reason: str
    rejection_reason: str | None = None
    decided_by_user_id: UUID | None = None
