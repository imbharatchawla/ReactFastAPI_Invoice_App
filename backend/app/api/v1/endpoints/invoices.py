from datetime import date, timedelta
import calendar
import json
import logging
import traceback
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from decimal import Decimal
from uuid import UUID
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, permission_dependency
from app.db.session import get_db
from app.models.bank import BankAccount
from app.models.client import Client
from app.models.client_access import UserClientAccess
from app.models.catalog import Company, Consultant, Milestone, Project
from app.models.invoice import Invoice, InvoiceRevertRequest, InvoiceFinalizationRequest
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceStatusUpdate, InvoiceUpdate, InvoiceRevertRequestCreate, InvoiceRevertRequestDecision, InvoiceRevertRequestRead, InvoiceFinalizationRequestCreate, InvoiceFinalizationRequestDecision, InvoiceFinalizationRequestRead, BulkRecurringInvoiceCreate, BulkRecurringInvoiceResult
from app.services.rbac import get_user_roles, has_permission

router = APIRouter(prefix="/invoices", tags=["invoices"])
logger = logging.getLogger(__name__)


class InvoicePdfRenderRequest(BaseModel):
    html: str = Field(..., min_length=1)
    filename: str | None = None

PROTECTED_INVOICE_STATUSES = {"issued", "payment_pending", "paid"}
PENDING_STATUS = "pending_final"


def normalize_invoice_status(status: str | None) -> str:
    value = str(status or "draft").strip().lower()
    if value == "final":
        return "issued"
    return value


def invoice_status_requires_approval(status: str | None) -> bool:
    return normalize_invoice_status(status) in PROTECTED_INVOICE_STATUSES


def invoice_is_protected_status(status: str | None) -> bool:
    return normalize_invoice_status(status) in PROTECTED_INVOICE_STATUSES


def status_label(status: str | None) -> str:
    labels = {"draft": "Draft", "issued": "Issued", "payment_pending": "Payment Pending", "paid": "Paid", "pending_final": "Pending Approval", "final": "Issued"}
    return labels.get(normalize_invoice_status(status), str(status or ""))


def validate_invoice_status_transition(invoice: Invoice, requested_status: str) -> None:
    current_status = normalize_invoice_status(invoice.status)
    if requested_status == "payment_pending" and current_status != "issued":
        raise HTTPException(status_code=400, detail="Payment Pending can only be selected after invoice status is Issued.")



def calculate_total(subtotal: Decimal, tax_amount: Decimal, expense_total: Decimal | None = None) -> Decimal:
    return (subtotal or Decimal("0.00")) + (tax_amount or Decimal("0.00")) + (expense_total or Decimal("0.00"))


def validate_project_monthly_consultant_periods(db: Session, data: dict) -> None:
    """For Project + Consultant invoices, monthly consultants need a valid start/end period."""
    if str(data.get("invoice_format") or "").lower() != "project" or data.get("billing_type") != "consultant_invoice":
        return
    try:
        meta = json.loads(data.get("expenses_json") or "{}")
    except Exception:
        return
    for line in meta.get("consultant_lines") or []:
        consultant_id = line.get("consultant_id")
        if not consultant_id:
            continue
        consultant = db.get(Consultant, consultant_id)
        billing_text = str((consultant.billing_type if consultant else None) or line.get("unit_label") or "").lower()
        if "month" not in billing_text:
            continue
        period_start = line.get("period_start")
        period_end = line.get("period_end")
        if not period_start or not period_end:
            raise HTTPException(status_code=400, detail="Monthly project consultant invoices require both period start date and period end date.")
        try:
            start_date = date.fromisoformat(str(period_start)[:10])
            end_date = date.fromisoformat(str(period_end)[:10])
        except ValueError:
            raise HTTPException(status_code=400, detail="Monthly project consultant invoice period dates must be valid dates.")
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Monthly project consultant invoice start date cannot be greater than end date.")


def resolve_project_currency_for_invoice(db: Session, data: dict) -> str | None:
    """Invoice currency must come from the selected/linked project only.

    Priority:
    1. Explicit invoice project_id
    2. First consultant line's linked project
    3. First milestone line's project
    4. First project linked to selected client/vendor
    """
    project_id = data.get("project_id")
    if project_id:
        project = db.get(Project, project_id)
        if project and project.currency:
            return project.currency

    try:
        meta = json.loads(data.get("expenses_json") or "{}")
    except Exception:
        meta = {}

    consultant_lines = meta.get("consultant_lines") or []
    for line in consultant_lines:
        consultant_id = line.get("consultant_id")
        if not consultant_id:
            continue
        consultant = db.get(Consultant, consultant_id)
        project = consultant.project if consultant else None
        if project and project.currency:
            return project.currency

    milestone_lines = meta.get("milestone_lines") or []
    for line in milestone_lines:
        line_project_id = line.get("project_id")
        if not line_project_id:
            continue
        project = db.get(Project, line_project_id)
        if project and project.currency:
            return project.currency

    client_id = data.get("client_id")
    if client_id:
        project = db.query(Project).filter(Project.client_id == client_id, Project.currency.isnot(None)).order_by(Project.name.asc()).first()
        if project and project.currency:
            return project.currency
    return None


def to_invoice_read(db: Session, invoice: Invoice) -> InvoiceRead:
    bank = db.get(BankAccount, invoice.bank_account_id) if invoice.bank_account_id else None
    return InvoiceRead(
        id=invoice.id,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        client_id=invoice.client_id,
        bank_account_id=invoice.bank_account_id,
        bank_details=bank,
        generated_by_user_id=invoice.generated_by_user_id,
        generated_by_name=invoice.generated_by.full_name if invoice.generated_by else None,
        generated_by_email=invoice.generated_by.email if invoice.generated_by else None,
        invoice_format=invoice.invoice_format,
        status=invoice.status,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        billing_type=invoice.billing_type,
        project_id=invoice.project_id,
        project_name=invoice.project.name if invoice.project else None,
        milestone_id=invoice.milestone_id,
        milestone_name=invoice.milestone.name if invoice.milestone else None,
        hours=invoice.hours,
        rate=invoice.rate,
        fee_amount=invoice.fee_amount,
        tax_label=invoice.tax_label,
        tax_percent=invoice.tax_percent,
        expense_total=invoice.expense_total,
        expenses_json=invoice.expenses_json,
        description=invoice.description,
        updated_by_user_id=invoice.updated_by_user_id,
        updated_by_name=invoice.updated_by.full_name if invoice.updated_by else None,
        updated_by_email=invoice.updated_by.email if invoice.updated_by else None,
        updated_on=invoice.updated_at,
    )


def user_has_unrestricted_invoice_client_access(current_user: User) -> bool:
    """Role-based shortcut for users that can work with all clients."""
    roles = set(get_user_roles(current_user))
    unrestricted_roles = {"admin", "finance", "bank_manager"}
    return current_user.is_superadmin or bool(roles.intersection(unrestricted_roles))


def user_can_select_all_invoice_clients(db: Session, current_user: User) -> bool:
    """Allow all invoice clients only for broad business roles.

    Access granted through a client-specific access request must stay scoped to
    that approved client/vendor, even when the granted permission is update or
    delete.
    """
    return user_has_unrestricted_invoice_client_access(current_user)


def get_approved_invoice_client_ids(db: Session, current_user: User) -> list[UUID]:
    return [row.client_id for row in db.query(UserClientAccess).filter(UserClientAccess.user_id == current_user.id).all()]


def apply_invoice_client_scope(query, db: Session, current_user: User):
    if user_can_select_all_invoice_clients(db, current_user):
        return query
    approved_client_ids = get_approved_invoice_client_ids(db, current_user)
    if not approved_client_ids:
        return query.filter(False)
    return query.filter(Invoice.client_id.in_(approved_client_ids))


def ensure_references_exist(
    db: Session,
    client_id: UUID,
    bank_account_id: UUID | None,
    project_id: UUID | None = None,
    milestone_id: UUID | None = None,
) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Client ID does not exist")
    if bank_account_id and not db.get(BankAccount, bank_account_id):
        raise HTTPException(status_code=400, detail="Bank ID does not exist")
    if project_id and not db.get(Project, project_id):
        raise HTTPException(status_code=400, detail="Project ID does not exist")
    if milestone_id:
        milestone = db.get(Milestone, milestone_id)
        if not milestone:
            raise HTTPException(status_code=400, detail="Milestone ID does not exist")
        if project_id and milestone.project_id != project_id:
            raise HTTPException(status_code=400, detail="Selected milestone does not belong to selected project")
    return client


def ensure_hr_client_invoice_access(db: Session, current_user: User, client_id: UUID) -> None:
    """Restrict client-scoped invoice users to approved clients/vendors only."""
    if user_can_select_all_invoice_clients(db, current_user):
        return
    has_client_access = db.get(UserClientAccess, {"user_id": current_user.id, "client_id": client_id})
    if not has_client_access:
        raise HTTPException(status_code=403, detail="You can create or update invoices only for approved client/vendor IDs")


def require_invoice_status_update_access(db: Session, current_user: User) -> None:
    roles = set(get_user_roles(current_user))
    if current_user.is_superadmin or "admin" in roles or has_permission(db, current_user, "invoices", "update"):
        return
    raise HTTPException(status_code=403, detail="Missing update access for invoices")


def require_superadmin_for_revert_decision(current_user: User) -> None:
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can approve or reject invoice draft revert requests")


def to_revert_request_read(row: InvoiceRevertRequest) -> InvoiceRevertRequestRead:
    return InvoiceRevertRequestRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        invoice_id=row.invoice_id,
        invoice_number=row.invoice.invoice_number if row.invoice else None,
        requester_id=row.requester_id,
        requester_name=row.requester.full_name if row.requester else None,
        requester_email=row.requester.email if row.requester else None,
        status=row.status,
        reason=row.reason,
        rejection_reason=row.rejection_reason,
        decided_by_user_id=row.decided_by_user_id,
    )



def to_finalization_request_read(row: InvoiceFinalizationRequest) -> InvoiceFinalizationRequestRead:
    return InvoiceFinalizationRequestRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        invoice_id=row.invoice_id,
        invoice_number=row.invoice.invoice_number if row.invoice else None,
        target_status=row.target_status or "issued",
        requester_id=row.requester_id,
        requester_name=row.requester.full_name if row.requester else None,
        requester_email=row.requester.email if row.requester else None,
        status=row.status,
        reason=row.reason,
        rejection_reason=row.rejection_reason,
        decided_by_user_id=row.decided_by_user_id,
    )


def is_admin_or_superadmin(current_user: User) -> bool:
    roles = set(get_user_roles(current_user))
    return current_user.is_superadmin or "admin" in roles


def create_pending_final_request(db: Session, invoice: Invoice, current_user: User, reason: str | None = None, target_status: str | None = None) -> None:
    existing = (
        db.query(InvoiceFinalizationRequest)
        .filter(InvoiceFinalizationRequest.invoice_id == invoice.id)
        .filter(InvoiceFinalizationRequest.status == "pending")
        .first()
    )
    requested_target = normalize_invoice_status(target_status or "issued")
    if requested_target not in PROTECTED_INVOICE_STATUSES:
        requested_target = "issued"
    if existing:
        existing.target_status = requested_target
        existing.reason = reason or f"Requested {status_label(requested_target)} approval"
        return
    row = InvoiceFinalizationRequest(
        invoice_id=invoice.id,
        requester_id=current_user.id,
        status="pending",
        reason=reason or f"Requested {status_label(requested_target)} approval",
        target_status=requested_target,
    )
    db.add(row)


def invoice_client_code(client: Client | None) -> str:
    raw = "".join(ch for ch in ((client.name if client else "") or "GEN").upper() if ch.isalnum())
    return (raw[:3] or "GEN").ljust(3, "X")


def invoice_year_month(invoice_date: date | None) -> str:
    value = invoice_date or date.today()
    return f"{value.year}{value.month:02d}"


def next_invoice_number(db: Session, client_id: UUID | None = None, invoice_date: date | None = None) -> str:
    """DYNE + 3 client letters + INV + YYYYMM + 4 digit sequence.

    The sequence is based primarily on the latest issued/final invoice for that
    client/month prefix, then checked against all invoices to keep drafts unique.
    """
    import re

    client = db.get(Client, client_id) if client_id else None
    prefix = f"DYNE{invoice_client_code(client)}INV{invoice_year_month(invoice_date)}"
    issued_rows = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .filter(Invoice.status.in_(["issued", "final"]))
        .all()
    )
    all_rows = db.query(Invoice.invoice_number).filter(Invoice.invoice_number.like(f"{prefix}%")).all()
    best_number = 0
    for (invoice_number,) in list(issued_rows) + list(all_rows):
        match = re.search(r"(\d{4})$", str(invoice_number or ""))
        if match:
            best_number = max(best_number, int(match.group(1)))
    return f"{prefix}{best_number + 1:04d}"


def unique_invoice_number(db: Session, preferred_number: str | None = None, client_id: UUID | None = None, invoice_date: date | None = None) -> str:
    """Return a unique invoice number, auto-incrementing if the preferred one is stale."""
    candidate = preferred_number or next_invoice_number(db, client_id=client_id, invoice_date=invoice_date)
    if not db.query(Invoice).filter(Invoice.invoice_number == candidate).first():
        return candidate
    return next_invoice_number(db, client_id=client_id, invoice_date=invoice_date)


@router.get("/next-number")
def get_next_invoice_number(client_id: UUID | None = None, invoice_date: date | None = None, _: User = Depends(permission_dependency("invoices", "create")), db: Session = Depends(get_db)):
    return {"invoice_number": next_invoice_number(db, client_id=client_id, invoice_date=invoice_date)}

@router.get("/lookups/clients")
def invoice_client_options(current_user: User = Depends(permission_dependency("invoices", "create")), db: Session = Depends(get_db)):
    """Dropdown options for invoice client selection.

    HR users only receive clients approved for them. Admin/superadmin/finance receive all clients.
    """
    query = db.query(Client)
    if not user_can_select_all_invoice_clients(db, current_user):
        query = query.join(UserClientAccess, UserClientAccess.client_id == Client.id).filter(UserClientAccess.user_id == current_user.id)
    clients = query.order_by(Client.name.asc()).all()
    options = []
    for client in clients:
        company_country = client.company.country if client.company else None
        is_india = any(str(country).strip().lower() == "india" for country in (client.countries or "").split(",")) or str(company_country or "").strip().lower() == "india"
        options.append({
            "id": str(client.id),
            "label": f"{client.name} - {client.details or (client.company.name if client.company else client.name)}",
            "name": client.name,
            "client_kind": client.client_kind,
            "email": client.email,
            "phone": client.phone,
            "details": client.details,
            "billing_address": client.billing_address,
            "tax_id": client.tax_id,
            "currency": client.currency,
            "client_currency": client.currency,
            "company_currency": client.company.currency if client.company else None,
            "company_name": client.company.name if client.company else None,
            "company_address": client.company.address if client.company else None,
            "company_tax_id": client.company.tax_id if client.company else None,
            "company_email": client.company.contact_email if client.company else None,
            "company_phone": client.company.contact_phone if client.company else None,
            "countries": [c.strip() for c in (client.countries or "").split(",") if c.strip()],
            "company_country": company_country,
            "tax_label": "GST" if is_india else "VAT",
            "tax_percent": str((client.company.gst_percent if is_india and client.company else None) or (client.company.vat_percent if client.company else None) or (Decimal("18.00") if is_india else Decimal("23.00"))),
            "bank_account_id": str(client.bank_account_id) if client.bank_account_id else None,
            "bank_account_label": f"{client.bank_account.bank_name} - {client.bank_account.account_holder_name}" if getattr(client, "bank_account", None) else None,
        })
    return options


@router.get("/lookups/banks")
def invoice_bank_options(_: User = Depends(permission_dependency("invoices", "create")), db: Session = Depends(get_db)):
    """Dropdown options for invoice bank account selection.

    This endpoint is protected by invoice create access so HR/finance users do not need separate bank module read access just to select a bank while creating an invoice.
    """
    banks = db.query(BankAccount).order_by(BankAccount.bank_name.asc()).all()
    return [
        {
            "id": str(bank.id),
            "label": f"{bank.bank_name} - {bank.account_holder_name}",
            "bank_name": bank.bank_name,
            "account_holder_name": bank.account_holder_name,
            "account_number": bank.account_number,
            "currency": bank.currency,
            "swift_code": bank.swift_code,
            "ifsc_code": bank.ifsc_code,
            "iban": bank.iban,
        }
        for bank in banks
    ]




@router.get("/lookups/projects")
def invoice_project_options(
    client_id: UUID | None = None,
    current_user: User = Depends(permission_dependency("invoices", "create")),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if client_id:
        query = query.filter(Project.client_id == client_id)
    if not user_can_select_all_invoice_clients(db, current_user):
        approved_client_ids = get_approved_invoice_client_ids(db, current_user)
        query = query.filter(Project.client_id.in_(approved_client_ids)) if approved_client_ids else query.filter(False)
    projects = query.order_by(Project.name.asc()).all()
    options = []
    for project in projects:
        client = project.client
        company_country = client.company.country if client and client.company else None
        is_india = False
        if client:
            is_india = any(str(country).strip().lower() == "india" for country in (client.countries or "").split(",")) or str(company_country or "").strip().lower() == "india"
        tax_label = "GST" if is_india else "VAT"
        tax_percent = Decimal("18.00") if is_india else Decimal("23.00")
        if client and client.company:
            tax_percent = (client.company.gst_percent if is_india else client.company.vat_percent) or tax_percent
        options.append({
            "id": str(project.id),
            "label": f"{project.name} - PO: {project.po_number}" if project.po_number else project.name,
            "name": project.name,
            "po_number": project.po_number,
            "client_id": str(project.client_id) if project.client_id else None,
            "client_name": client.name if client else None,
            "bank_account_id": str(client.bank_account_id) if client and client.bank_account_id else None,
            "currency": (project.currency or (client.currency if client else None)),
            "project_currency": project.currency,
            "client_currency": client.currency if client else None,
            "company_currency": client.company.currency if client and client.company else None,
            "company_name": client.company.name if client and client.company else None,
            "tax_label": tax_label,
            "tax_percent": str(tax_percent),
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "billing_rate": str(project.billing_rate or "0.00"),
            "billing_unit": project.billing_unit or "hours",
            "due_days": project.due_days or 0,
        })
    return options


@router.get("/lookups/milestones")
def invoice_milestone_options(
    project_id: UUID | None = None,
    current_user: User = Depends(permission_dependency("invoices", "create")),
    db: Session = Depends(get_db),
):
    query = db.query(Milestone).join(Project, Project.id == Milestone.project_id)
    if project_id:
        query = query.filter(Milestone.project_id == project_id)
    if not user_can_select_all_invoice_clients(db, current_user):
        approved_client_ids = get_approved_invoice_client_ids(db, current_user)
        query = query.filter(Project.client_id.in_(approved_client_ids)) if approved_client_ids else query.filter(False)
    milestones = query.order_by(Milestone.name.asc()).all()
    return [{"id": str(milestone.id), "label": milestone.name, "project_id": str(milestone.project_id)} for milestone in milestones]


@router.get("/lookups/consultants")
def invoice_consultant_options(
    project_id: UUID | None = None,
    current_user: User = Depends(permission_dependency("invoices", "create")),
    db: Session = Depends(get_db),
):
    query = db.query(Consultant).outerjoin(Project, Project.id == Consultant.project_id)
    if project_id:
        query = query.filter(Consultant.project_id == project_id)
    if not user_can_select_all_invoice_clients(db, current_user):
        approved_client_ids = get_approved_invoice_client_ids(db, current_user)
        query = query.filter(Project.client_id.in_(approved_client_ids)) if approved_client_ids else query.filter(False)
    consultants = query.order_by(Consultant.name.asc()).all()
    options = []
    for consultant in consultants:
        project = consultant.project
        client = project.client if project else None
        options.append({
            "id": str(consultant.id),
            "label": consultant.name,
            "name": consultant.name,
            "first_name": consultant.first_name,
            "last_name": consultant.last_name,
            "project_id": str(consultant.project_id) if consultant.project_id else None,
            "client_id": str(client.id) if client else None,
            "bank_account_id": str(client.bank_account_id) if client and client.bank_account_id else None,
            "billing_type": consultant.billing_type,
            "rate": str((project.billing_rate if project and project.billing_rate is not None else consultant.rate) or "0.00"),
            "project_billing_rate": str(project.billing_rate or "0.00") if project else None,
            "project_billing_unit": project.billing_unit or "hours" if project else "hours",
            "currency": ((project.currency if project else None) or (client.currency if client else None) or consultant.currency),
            "project_currency": project.currency if project else None,
            "consultant_currency": consultant.currency,
            "client_currency": client.currency if client else None,
            "company_currency": client.company.currency if client and client.company else None,
            "company_name": client.company.name if client and client.company else None,
            "po_detail": consultant.po_detail,
            "start_date": consultant.start_date.isoformat() if consultant.start_date else None,
            "end_date": consultant.end_date.isoformat() if consultant.end_date else None,
        })
    return options


@router.get("/lookups/expense-descriptions")
def invoice_expense_description_options(
    _: User = Depends(permission_dependency("invoices", "create")),
    db: Session = Depends(get_db),
):
    """Return distinct historical expense descriptions for type-ahead suggestions."""
    import json

    values: set[str] = set()
    for row in db.query(Invoice.expenses_json).filter(Invoice.expenses_json.isnot(None)).limit(500).all():
        try:
            parsed = json.loads(row[0] or "{}")
            expenses = parsed.get("expenses", []) if isinstance(parsed, dict) else []
            for exp in expenses:
                desc = str(exp.get("description") or "").strip()
                if desc:
                    values.add(desc)
        except Exception:
            continue
    return sorted(values)[:100]



def month_last_date(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def recurring_consultant_is_active(consultant: Consultant, invoice_date: date) -> bool:
    if consultant.start_date and consultant.start_date > invoice_date:
        return False
    if consultant.end_date and consultant.end_date < invoice_date:
        return False
    return True


def latest_consultant_invoice_line(db: Session, consultant: Consultant) -> dict | None:
    needle = str(consultant.id)
    rows = (
        db.query(Invoice)
        .filter(Invoice.billing_type == "consultant_invoice")
        .filter(Invoice.expenses_json.isnot(None))
        .order_by(Invoice.invoice_date.desc().nullslast(), Invoice.created_at.desc())
        .limit(300)
        .all()
    )
    for invoice in rows:
        if needle not in (invoice.expenses_json or ""):
            continue
        try:
            parsed = json.loads(invoice.expenses_json or "{}")
            for line in parsed.get("consultant_lines", []):
                if str(line.get("consultant_id")) == needle:
                    return line
        except Exception:
            continue
    return None


@router.post("/bulk-recurring", response_model=BulkRecurringInvoiceResult)
def create_bulk_recurring_invoices(payload: BulkRecurringInvoiceCreate, current_user: User = Depends(permission_dependency("invoices", "create")), db: Session = Depends(get_db)):
    invoice_date = month_last_date(payload.year, payload.month)
    month_start = date(payload.year, payload.month, 1)
    consultants = db.query(Consultant).filter(Consultant.is_recurring_invoice == True).order_by(Consultant.name.asc()).all()  # noqa: E712
    created_rows = []
    skipped: list[str] = []

    for consultant in consultants:
        label = consultant.name or str(consultant.id)
        if not recurring_consultant_is_active(consultant, invoice_date):
            skipped.append(f"{label}: outside start/end date for selected month")
            continue
        project = consultant.project
        client = project.client if project else None
        if not project or not client:
            skipped.append(f"{label}: project/client mapping missing")
            continue
        try:
            ensure_hr_client_invoice_access(db, current_user, client.id)
        except HTTPException:
            skipped.append(f"{label}: current user has no invoice access for client {client.name}")
            continue
        duplicate = False
        existing_rows = db.query(Invoice).filter(Invoice.invoice_date >= month_start, Invoice.invoice_date <= invoice_date, Invoice.billing_type == "consultant_invoice").all()
        for existing in existing_rows:
            if str(consultant.id) in (existing.expenses_json or ""):
                duplicate = True
                break
        if duplicate:
            skipped.append(f"{label}: invoice already exists for selected month")
            continue

        previous_line = latest_consultant_invoice_line(db, consultant) or {}
        units = Decimal(str(previous_line.get("hours") or "1.00"))
        rate = Decimal(str((project.billing_rate if project and project.billing_rate is not None else None) or previous_line.get("rate") or consultant.rate or "0.00"))
        subtotal = units * rate
        tax_label = "GST" if any(str(country).strip().lower() == "india" for country in (client.countries or client.country or "").split(",")) else "VAT"
        tax_percent = Decimal("18.00") if tax_label == "GST" else Decimal("23.00")
        if client.company:
            tax_percent = client.company.gst_percent if tax_label == "GST" else client.company.vat_percent
            tax_percent = tax_percent or (Decimal("18.00") if tax_label == "GST" else Decimal("23.00"))
        tax_amount = subtotal * tax_percent / Decimal("100")
        meta = {
            "consultant_lines": [{
                "consultant_id": str(consultant.id),
                "consultant_name": consultant.name,
                "hours": str(units),
                "rate": str(rate),
                "amount": str(subtotal),
            }],
            "milestone_lines": [],
            "generic_lines": [],
            "consultant_notes": "Auto-generated recurring monthly invoice.",
            "expense_notes": "",
            "generic_notes": "",
            "expenses": [],
        }
        invoice = Invoice(
            invoice_number=unique_invoice_number(db, client_id=client.id, invoice_date=invoice_date),
            invoice_date=invoice_date,
            due_date=invoice_date + timedelta(days=int(project.due_days or 0)),
            client_id=client.id,
            bank_account_id=client.bank_account_id,
            generated_by_user_id=current_user.id,
            invoice_format="staffing",
            status=normalize_invoice_status(payload.status.value if hasattr(payload.status, "value") else str(payload.status)),
            currency=(project.currency or client.currency or consultant.currency or "INR"),
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=calculate_total(subtotal, tax_amount, Decimal("0.00")),
            billing_type="consultant_invoice",
            project_id=project.id,
            hours=units,
            rate=rate,
            fee_amount=subtotal,
            tax_label=tax_label,
            tax_percent=tax_percent,
            expense_total=Decimal("0.00"),
            expenses_json=json.dumps(meta),
            description="Auto-generated recurring monthly invoice.",
        )
        requested_status = normalize_invoice_status(invoice.status)
        if invoice_status_requires_approval(requested_status) and not is_admin_or_superadmin(current_user):
            invoice.status = PENDING_STATUS
        db.add(invoice)
        db.flush()
        if invoice.status == PENDING_STATUS:
            create_pending_final_request(db, invoice, current_user, target_status=requested_status)
        created_rows.append(invoice)

    db.commit()
    for row in created_rows:
        db.refresh(row)
    return BulkRecurringInvoiceResult(
        created_count=len(created_rows),
        skipped_count=len(skipped),
        created=[to_invoice_read(db, row) for row in created_rows],
        skipped=skipped,
    )


@router.get("", response_model=list[InvoiceRead])
def list_invoices(current_user: User = Depends(permission_dependency("invoices", "read")), db: Session = Depends(get_db)):
    query = apply_invoice_client_scope(db.query(Invoice), db, current_user)
    rows = query.order_by(Invoice.created_at.desc()).all()
    return [to_invoice_read(db, row) for row in rows]



def resolve_project_due_date_for_invoice(db: Session, data: dict) -> date | None:
    """Calculate invoice due date from linked project due days when available."""
    invoice_date_value = data.get("invoice_date")
    if not invoice_date_value:
        return data.get("due_date")

    project_id = data.get("project_id")
    if not project_id:
        try:
            meta = json.loads(data.get("expenses_json") or "{}")
        except Exception:
            meta = {}
        consultant_lines = meta.get("consultant_lines") or []
        for line in consultant_lines:
            consultant_id = line.get("consultant_id")
            if consultant_id:
                consultant = db.get(Consultant, consultant_id)
                if consultant and consultant.project_id:
                    project_id = consultant.project_id
                    break
        if not project_id:
            milestone_lines = meta.get("milestone_lines") or []
            for line in milestone_lines:
                if line.get("project_id"):
                    project_id = line.get("project_id")
                    break
    if not project_id:
        return data.get("due_date") or invoice_date_value
    project = db.get(Project, project_id)
    if not project or project.due_days is None:
        return data.get("due_date") or invoice_date_value
    try:
        return invoice_date_value + timedelta(days=int(project.due_days or 0))
    except Exception:
        return data.get("due_date") or invoice_date_value

@router.post("", response_model=InvoiceRead)
def create_invoice(payload: InvoiceCreate, current_user: User = Depends(permission_dependency("invoices", "create")), db: Session = Depends(get_db)):
    generated_number = unique_invoice_number(db, payload.invoice_number, client_id=payload.client_id, invoice_date=payload.invoice_date)
    ensure_references_exist(db, payload.client_id, payload.bank_account_id, payload.project_id, payload.milestone_id)
    ensure_hr_client_invoice_access(db, current_user, payload.client_id)
    data = payload.model_dump()
    data["invoice_number"] = generated_number
    validate_project_monthly_consultant_periods(db, data)
    project_currency = resolve_project_currency_for_invoice(db, data)
    if project_currency:
        data["currency"] = project_currency
    if not data.get("due_date"):
        data["due_date"] = resolve_project_due_date_for_invoice(db, data)
    if data.get("billing_type") == "consultant_invoice" and data.get("hours") is not None and data.get("rate") is not None:
        data["fee_amount"] = (data["hours"] or Decimal("0.00")) * (data["rate"] or Decimal("0.00"))
        data["subtotal"] = data["fee_amount"]
    elif data.get("fee_amount") is not None:
        data["subtotal"] = data["fee_amount"]
    data["expense_total"] = data.get("expense_total") or Decimal("0.00")
    data["total_amount"] = calculate_total(data["subtotal"], data["tax_amount"], data["expense_total"])
    data["generated_by_user_id"] = current_user.id
    requested_status = normalize_invoice_status(data.get("status"))
    data["status"] = requested_status
    requested_protected_status = invoice_status_requires_approval(requested_status)
    if requested_protected_status and not is_admin_or_superadmin(current_user):
        data["status"] = PENDING_STATUS
    invoice = Invoice(**data)
    db.add(invoice)
    db.flush()
    if requested_protected_status and not is_admin_or_superadmin(current_user):
        create_pending_final_request(db, invoice, current_user, target_status=requested_status)
    db.commit()
    db.refresh(invoice)
    return to_invoice_read(db, invoice)


@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
def change_invoice_status(
    invoice_id: UUID,
    payload: InvoiceStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Allow users with invoice update access to change status."""
    require_invoice_status_update_access(db, current_user)
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    ensure_hr_client_invoice_access(db, current_user, invoice.client_id)
    requested_status = normalize_invoice_status(payload.status.value if hasattr(payload.status, "value") else payload.status)
    validate_invoice_status_transition(invoice, requested_status)
    if invoice_status_requires_approval(requested_status) and not is_admin_or_superadmin(current_user):
        invoice.status = PENDING_STATUS
        invoice.updated_by_user_id = current_user.id
        create_pending_final_request(db, invoice, current_user, target_status=requested_status)
    else:
        invoice.status = requested_status
        invoice.updated_by_user_id = current_user.id
    db.commit()
    db.refresh(invoice)
    return to_invoice_read(db, invoice)


@router.put("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: UUID, payload: InvoiceUpdate, current_user: User = Depends(permission_dependency("invoices", "update")), db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    data = payload.model_dump(exclude_unset=True)
    target_client_id = data.get("client_id", invoice.client_id)
    target_bank_id = data.get("bank_account_id", invoice.bank_account_id)
    target_project_id = data.get("project_id", invoice.project_id)
    target_milestone_id = data.get("milestone_id", invoice.milestone_id)
    ensure_references_exist(db, target_client_id, target_bank_id, target_project_id, target_milestone_id)
    ensure_hr_client_invoice_access(db, current_user, target_client_id)
    validation_data = {**{"client_id": target_client_id, "project_id": target_project_id, "invoice_format": data.get("invoice_format", invoice.invoice_format), "billing_type": data.get("billing_type", invoice.billing_type), "expenses_json": data.get("expenses_json", invoice.expenses_json)}, **data}
    validate_project_monthly_consultant_periods(db, validation_data)
    project_currency = resolve_project_currency_for_invoice(db, {**{"client_id": target_client_id, "project_id": target_project_id}, **data})
    if project_currency:
        data["currency"] = project_currency
    if "due_date" not in data or not data.get("due_date"):
        data["due_date"] = resolve_project_due_date_for_invoice(db, {**{"client_id": target_client_id, "project_id": target_project_id, "invoice_date": data.get("invoice_date", invoice.invoice_date), "expenses_json": data.get("expenses_json", invoice.expenses_json)}, **data})
    requested_status = normalize_invoice_status(data.get("status")) if "status" in data else None
    for key, value in data.items():
        if key == "status":
            normalized_value = normalize_invoice_status(value)
            if invoice_status_requires_approval(normalized_value) and not is_admin_or_superadmin(current_user):
                setattr(invoice, key, PENDING_STATUS)
            else:
                setattr(invoice, key, normalized_value)
        else:
            setattr(invoice, key, value)
    invoice.updated_by_user_id = current_user.id
    if requested_status and invoice_status_requires_approval(requested_status) and not is_admin_or_superadmin(current_user):
        create_pending_final_request(db, invoice, current_user, target_status=requested_status)
    if invoice.billing_type == "consultant_invoice" and invoice.hours is not None and invoice.rate is not None:
        invoice.fee_amount = invoice.hours * invoice.rate
        invoice.subtotal = invoice.fee_amount
    elif invoice.fee_amount is not None:
        invoice.subtotal = invoice.fee_amount
    invoice.total_amount = calculate_total(invoice.subtotal, invoice.tax_amount, invoice.expense_total)
    db.commit()
    db.refresh(invoice)
    return to_invoice_read(db, invoice)


@router.get("/finalization-requests", response_model=list[InvoiceFinalizationRequestRead])
def list_invoice_finalization_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List invoice status approval requests. Admin/superadmin see all, users see their own."""
    query = db.query(InvoiceFinalizationRequest).order_by(InvoiceFinalizationRequest.created_at.desc())
    if not is_admin_or_superadmin(current_user):
        query = query.filter(InvoiceFinalizationRequest.requester_id == current_user.id)
    return [to_finalization_request_read(row) for row in query.all()]


@router.post("/{invoice_id}/finalization-requests", response_model=InvoiceFinalizationRequestRead)
def create_invoice_finalization_request(
    invoice_id: UUID,
    payload: InvoiceFinalizationRequestCreate | None = None,
    current_user: User = Depends(permission_dependency("invoices", "update")),
    db: Session = Depends(get_db),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    ensure_hr_client_invoice_access(db, current_user, invoice.client_id)
    if is_admin_or_superadmin(current_user):
        raise HTTPException(status_code=400, detail="Admin and superadmin can change invoice status directly")
    target_status = normalize_invoice_status(payload.target_status if payload and payload.target_status else "issued")
    if target_status not in PROTECTED_INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid target invoice status")
    validate_invoice_status_transition(invoice, target_status)
    if invoice.status == target_status:
        raise HTTPException(status_code=400, detail=f"Invoice is already {status_label(target_status)}")
    if invoice.status != PENDING_STATUS:
        invoice.status = PENDING_STATUS
        invoice.updated_by_user_id = current_user.id
    create_pending_final_request(db, invoice, current_user, payload.reason if payload else None, target_status=target_status)
    db.commit()
    row = (
        db.query(InvoiceFinalizationRequest)
        .filter(InvoiceFinalizationRequest.invoice_id == invoice_id)
        .filter(InvoiceFinalizationRequest.status == "pending")
        .order_by(InvoiceFinalizationRequest.created_at.desc())
        .first()
    )
    return to_finalization_request_read(row)


@router.patch("/finalization-requests/{request_id}/decision", response_model=InvoiceFinalizationRequestRead)
def decide_invoice_finalization_request(
    request_id: UUID,
    payload: InvoiceFinalizationRequestDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_admin_or_superadmin(current_user):
        raise HTTPException(status_code=403, detail="Only admin or superadmin can approve/reject invoice status requests")
    row = db.get(InvoiceFinalizationRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Invoice status request not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be decided")
    decision = payload.status.lower()
    if decision == "approved":
        row.invoice.status = normalize_invoice_status(row.target_status or "issued")
        row.invoice.updated_by_user_id = current_user.id
        row.status = "approved"
        row.rejection_reason = None
    else:
        row.invoice.status = "draft"
        row.invoice.updated_by_user_id = current_user.id
        row.status = "rejected"
        row.rejection_reason = payload.rejection_reason or "Rejected by admin"
    row.decided_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return to_finalization_request_read(row)


@router.get("/revert-requests", response_model=list[InvoiceRevertRequestRead])
def list_invoice_revert_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List revert-to-draft requests.

    Superadmin sees all requests. Normal users see only their own requests.
    """
    query = db.query(InvoiceRevertRequest).order_by(InvoiceRevertRequest.created_at.desc())
    if not current_user.is_superadmin:
        query = query.filter(InvoiceRevertRequest.requester_id == current_user.id)
    return [to_revert_request_read(row) for row in query.all()]


@router.post("/{invoice_id}/revert-requests", response_model=InvoiceRevertRequestRead)
def create_invoice_revert_request(
    invoice_id: UUID,
    payload: InvoiceRevertRequestCreate,
    current_user: User = Depends(permission_dependency("invoices", "read")),
    db: Session = Depends(get_db),
):
    """Ask superadmin to revert an issued/payment invoice back to draft."""
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    ensure_hr_client_invoice_access(db, current_user, invoice.client_id)
    if not invoice_is_protected_status(invoice.status):
        raise HTTPException(status_code=400, detail="Only issued, payment pending, or paid invoices can be requested for draft revert")
    if current_user.is_superadmin or "admin" in set(get_user_roles(current_user)):
        raise HTTPException(status_code=400, detail="Admin and superadmin can change invoice status directly")
    existing = (
        db.query(InvoiceRevertRequest)
        .filter(InvoiceRevertRequest.invoice_id == invoice_id)
        .filter(InvoiceRevertRequest.requester_id == current_user.id)
        .filter(InvoiceRevertRequest.status == "pending")
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="A pending draft revert request already exists for this invoice")
    row = InvoiceRevertRequest(invoice_id=invoice_id, requester_id=current_user.id, reason=payload.reason.strip(), status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_revert_request_read(row)


@router.patch("/revert-requests/{request_id}/decision", response_model=InvoiceRevertRequestRead)
def decide_invoice_revert_request(
    request_id: UUID,
    payload: InvoiceRevertRequestDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Superadmin approves/rejects reverting issued/payment invoice back to draft."""
    require_superadmin_for_revert_decision(current_user)
    row = db.get(InvoiceRevertRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Draft revert request not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be decided")
    decision = payload.status.lower()
    if decision == "approved":
        row.invoice.status = "draft"
        row.invoice.updated_by_user_id = current_user.id
        row.status = "approved"
        row.rejection_reason = None
    else:
        row.status = "rejected"
        row.rejection_reason = payload.rejection_reason or "Rejected by superadmin"
    row.decided_by_user_id = current_user.id
    db.commit()
    db.refresh(row)
    return to_revert_request_read(row)



@router.post("/render-pdf")
def render_invoice_pdf(
    payload: InvoicePdfRenderRequest,
    _: User = Depends(permission_dependency("invoices", "read")),
):
    """Render invoice HTML to PDF using the same browser print engine.

    Important: do not use html2canvas/html2pdf here. Those libraries rasterize the
    invoice and were producing faded/unformatted PDFs. This endpoint writes the
    exact print HTML to a temporary file and asks installed Chrome/Edge to run
    headless `--print-to-pdf`, which is the closest programmatic equivalent of
    Chrome Print -> Save as PDF.
    """

    def _format_invoice_pdf_filename(raw_filename: str) -> str:
        """
        Converts old invoice filename format:

            DYNENTTINV2026040001.pdf

        into:

            DYNE-NTT-INV2026040001.pdf

        Rule:
        - Prefix must become DYNE-
        - Client short code comes between DYNE- and -INV
        - Invoice number starts from INV...
        """
        name = (raw_filename or "invoice.pdf").replace('"', "").replace("\r", "").replace("\n", "").strip()

        if name.lower().endswith(".pdf"):
            name_without_ext = name[:-4]
        else:
            name_without_ext = name

        # Already formatted correctly
        if re.match(r"^DYNE-[A-Z0-9]+-INV\d+", name_without_ext, re.IGNORECASE):
            return f"{name_without_ext}.pdf"

        # Convert DYNENTTINV2026040001 -> DYNE-NTT-INV2026040001
        match = re.match(r"^DYNE([A-Z0-9]+)(INV\d+)$", name_without_ext, re.IGNORECASE)
        if match:
            client_code = match.group(1).upper()
            invoice_part = match.group(2).upper()
            return f"DYNE-{client_code}-{invoice_part}.pdf"

        # Fallback: if it only contains INV somewhere
        inv_index = name_without_ext.upper().find("INV")
        if inv_index > 0:
            before_inv = name_without_ext[:inv_index]
            invoice_part = name_without_ext[inv_index:].upper()

            if before_inv.upper().startswith("DYNE"):
                client_code = before_inv[4:].upper()
                if client_code:
                    return f"DYNE-{client_code}-{invoice_part}.pdf"

        # Safe fallback
        return f"{name_without_ext}.pdf"


    html = payload.html or ""
    filename = _format_invoice_pdf_filename(payload.filename or "invoice.pdf")
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    def _candidate_browsers() -> list[str]:
        candidates: list[str] = []

        # Explicit override, useful when Chrome/Edge is installed in a custom path.
        for env_name in ("CHROME_PATH", "EDGE_PATH", "CHROMIUM_PATH"):
            env_path = os.environ.get(env_name)
            if env_path:
                candidates.append(env_path)

        # PATH lookup.
        for cmd in (
            "chrome",
            "chrome.exe",
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "msedge",
            "msedge.exe",
        ):
            found = shutil.which(cmd)
            if found:
                candidates.append(found)

        # Common Windows install locations.
        local_app = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
        candidates.extend([
            os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local_app, "Microsoft", "Edge", "Application", "msedge.exe"),
        ])

        unique: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            item = os.path.abspath(os.path.expanduser(item))
            key = item.lower()
            if key not in seen and os.path.exists(item):
                unique.append(item)
                seen.add(key)
        return unique

    tmp_dir = tempfile.mkdtemp(prefix="invoice_pdf_")
    try:
        html_path = Path(tmp_dir) / "invoice.html"
        pdf_path = Path(tmp_dir) / filename

        # A base tag helps Chrome resolve any relative asset paths if present.
        if "<head" in html.lower() and "<base " not in html.lower():
            html = html.replace("<head>", '<head><base href="http://localhost/">', 1)
            html = html.replace("<head >", '<head><base href="http://localhost/">', 1)

        html_path.write_text(html, encoding="utf-8")
        file_url = html_path.resolve().as_uri()

        browsers = _candidate_browsers()
        if not browsers:
            raise RuntimeError(
                "Google Chrome or Microsoft Edge was not found on the backend machine. "
                "Install Chrome/Edge or set CHROME_PATH to chrome.exe."
            )

        errors: list[str] = []
        for browser_path in browsers:
            cmd = [
                browser_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--allow-file-access-from-files",
                "--disable-web-security",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=7000",
                f"--print-to-pdf={str(pdf_path)}",
                "--print-to-pdf-no-header",
                file_url,
            ]
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 1000:
                    pdf_bytes = pdf_path.read_bytes()
                    return Response(
                        content=pdf_bytes,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                    )
                errors.append(
                    f"{browser_path}: returncode={result.returncode}, "
                    f"stdout={result.stdout.decode(errors='ignore')[:300]}, "
                    f"stderr={result.stderr.decode(errors='ignore')[:500]}"
                )
            except Exception as browser_exc:
                errors.append(f"{browser_path}: {browser_exc}")

        raise RuntimeError("Chrome/Edge PDF generation failed. " + " | ".join(errors))
    except Exception as exc:
        logger.exception("Invoice PDF render failed")
        print("Invoice PDF render failed:", repr(exc))
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Unable to render PDF automatically using Chrome/Edge. Server error: " + str(exc)[:1200],
        ) from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: UUID, _: User = Depends(permission_dependency("invoices", "delete")), db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted"}
