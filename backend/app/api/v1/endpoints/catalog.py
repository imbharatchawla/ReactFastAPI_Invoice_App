from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import permission_dependency
from app.db.session import get_db
from app.models.catalog import Company, Consultant, Milestone, Project
from app.models.client import Client
from app.models.bank import BankAccount
from app.models.user import User
from app.schemas.catalog import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    ConsultantCreate,
    ConsultantRead,
    ConsultantUpdate,
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)

companies_router = APIRouter(prefix="/companies", tags=["companies"])
projects_router = APIRouter(prefix="/projects", tags=["projects"])
milestones_router = APIRouter(prefix="/milestones", tags=["milestones"])
consultants_router = APIRouter(prefix="/consultants", tags=["consultants"])


class RecurringConsultantsUpdate(BaseModel):
    consultant_ids: list[UUID] = []




def ensure_end_date_after_start_date(start_date, end_date, label: str) -> None:
    if start_date and end_date and end_date <= start_date:
        raise HTTPException(status_code=400, detail=f"{label} end date must be greater than start date")



def normalize_company_tax(country: str | None) -> tuple[Decimal, Decimal]:
    """Return VAT/GST according to country rule.

    Business default rule:
    - India: GST 18%, VAT 0%
    - Any other country: VAT 23%, GST 0%
    The fields remain editable in create/update payloads.
    """
    if (country or "").strip().lower() == "india":
        return Decimal("0.00"), Decimal("18.00")
    return Decimal("23.00"), Decimal("0.00")




def default_currency_for_country(country: str | None) -> str:
    mapping = {
        "india": "INR",
        "ireland": "EUR",
        "united states": "USD",
        "united kingdom": "GBP",
        "united arab emirates": "AED",
        "singapore": "SGD",
        "south africa": "ZAR",
        "australia": "AUD",
        "new zealand": "NZD",
        "canada": "CAD",
        "germany": "EUR",
        "france": "EUR",
        "netherlands": "EUR",
    }
    return mapping.get((country or "").strip().lower(), "INR")

def apply_company_tax_rule(data: dict) -> dict:
    vat, gst = normalize_company_tax(data.get("country"))
    data["vat_percent"] = vat
    data["gst_percent"] = gst
    return data


def apply_company_tax_rule_to_row(row: Company) -> None:
    row.vat_percent, row.gst_percent = normalize_company_tax(row.country)


def company_read(row: Company) -> CompanyRead:
    data = CompanyRead.model_validate(row)
    data.bank_account_ids = [bank.id for bank in (row.bank_accounts or [])]
    data.bank_account_labels = [f"{bank.bank_name} - {bank.account_holder_name}" for bank in (row.bank_accounts or [])]
    return data


def apply_company_bank_links(db: Session, row: Company, bank_account_ids):
    if bank_account_ids is None:
        return
    ids = [bank_id for bank_id in bank_account_ids if bank_id]
    if not ids:
        row.bank_accounts = []
        return
    banks = db.query(BankAccount).filter(BankAccount.id.in_(ids)).all()
    if len(banks) != len(set(ids)):
        raise HTTPException(status_code=400, detail="One or more selected bank accounts do not exist")
    row.bank_accounts = banks


def project_read(row: Project) -> ProjectRead:
    data = ProjectRead.model_validate(row)
    data.company_name = row.company.name if row.company else None
    data.client_name = row.client.name if row.client else None
    return data


def milestone_read(row: Milestone) -> MilestoneRead:
    data = MilestoneRead.model_validate(row)
    data.project_name = row.project.name if row.project else None
    data.client_name = row.project.client.name if row.project and row.project.client else None
    return data




def normalize_optional_text(value):
    """Convert blank optional text values to None so optional unique fields stay optional."""
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


def normalize_consultant_optional_fields(data: dict) -> dict:
    """Normalize consultant optional fields before validation/database writes."""
    if "po_detail" in data:
        data["po_detail"] = normalize_optional_text(data.get("po_detail"))
    return data

def consultant_full_name(data: dict) -> str:
    first = str(data.get("first_name") or "").strip()
    last = str(data.get("last_name") or "").strip()
    full = " ".join([part for part in [first, last] if part]).strip()
    return full or str(data.get("name") or "").strip()


def consultant_read(row: Consultant) -> ConsultantRead:
    # Keep returned name aligned with first + last name for dropdowns/tables.
    if (row.first_name or row.last_name) and row.name != f"{row.first_name or ''} {row.last_name or ''}".strip():
        row.name = f"{row.first_name or ''} {row.last_name or ''}".strip()
    data = ConsultantRead.model_validate(row)
    data.project_name = row.project.name if row.project else None
    data.client_name = row.project.client.name if row.project and row.project.client else None
    return data


@companies_router.get("", response_model=list[CompanyRead])
def list_companies(_: User = Depends(permission_dependency("companies", "read")), db: Session = Depends(get_db)):
    rows = db.query(Company).order_by(Company.created_at.desc()).all()
    return [company_read(row) for row in rows]


@companies_router.post("", response_model=CompanyRead)
def create_company(payload: CompanyCreate, _: User = Depends(permission_dependency("companies", "create")), db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("currency"):
        data["currency"] = default_currency_for_country(data.get("country"))
    if data.get("vat_percent") is None or data.get("gst_percent") is None:
        vat, gst = normalize_company_tax(data.get("country"))
        data["vat_percent"] = vat if data.get("vat_percent") is None else data.get("vat_percent")
        data["gst_percent"] = gst if data.get("gst_percent") is None else data.get("gst_percent")
    bank_account_ids = data.pop("bank_account_ids", None)
    row = Company(**data)
    apply_company_bank_links(db, row, bank_account_ids)
    db.add(row)
    db.commit()
    db.refresh(row)
    return company_read(row)


@companies_router.put("/{company_id}", response_model=CompanyRead)
def update_company(company_id: UUID, payload: CompanyUpdate, _: User = Depends(permission_dependency("companies", "update")), db: Session = Depends(get_db)):
    row = db.get(Company, company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    data = payload.model_dump(exclude_unset=True)
    if "country" in data and "currency" not in data:
        data["currency"] = default_currency_for_country(data.get("country"))
    bank_account_ids = data.pop("bank_account_ids", None)
    for key, value in data.items():
        setattr(row, key, value)
    apply_company_bank_links(db, row, bank_account_ids)
    db.commit()
    db.refresh(row)
    return company_read(row)


@companies_router.delete("/{company_id}")
def delete_company(company_id: UUID, _: User = Depends(permission_dependency("companies", "delete")), db: Session = Depends(get_db)):
    row = db.get(Company, company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(row)
    db.commit()
    return {"message": "Company deleted"}


@projects_router.get("", response_model=list[ProjectRead])
def list_projects(_: User = Depends(permission_dependency("projects", "read")), db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.created_at.desc()).all()
    return [project_read(row) for row in rows]


@projects_router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, _: User = Depends(permission_dependency("projects", "create")), db: Session = Depends(get_db)):
    if payload.client_id and not db.get(Client, payload.client_id):
        raise HTTPException(status_code=400, detail="Client does not exist")
    if payload.company_id and not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail="Company does not exist")
    data = payload.model_dump()
    if not data.get("currency") and data.get("client_id"):
        client = db.get(Client, data.get("client_id"))
        data["currency"] = client.currency if client and client.currency else "INR"
    data["currency"] = data.get("currency") or "INR"
    data["start_date"] = data.get("start_date") or __import__("datetime").date(2026, 1, 1)
    data["end_date"] = data.get("end_date") or __import__("datetime").date(2026, 12, 31)
    ensure_end_date_after_start_date(data.get("start_date"), data.get("end_date"), "Project")
    row = Project(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return project_read(row)


@projects_router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: UUID, payload: ProjectUpdate, _: User = Depends(permission_dependency("projects", "update")), db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("client_id") and not db.get(Client, data["client_id"]):
        raise HTTPException(status_code=400, detail="Client does not exist")
    if data.get("company_id") and not db.get(Company, data["company_id"]):
        raise HTTPException(status_code=400, detail="Company does not exist")
    target_start = data.get("start_date", row.start_date)
    target_end = data.get("end_date", row.end_date)
    ensure_end_date_after_start_date(target_start, target_end, "Project")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return project_read(row)


@projects_router.delete("/{project_id}")
def delete_project(project_id: UUID, _: User = Depends(permission_dependency("projects", "delete")), db: Session = Depends(get_db)):
    row = db.get(Project, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(row)
    db.commit()
    return {"message": "Project deleted"}


@milestones_router.get("", response_model=list[MilestoneRead])
def list_milestones(_: User = Depends(permission_dependency("milestones", "read")), db: Session = Depends(get_db)):
    rows = db.query(Milestone).order_by(Milestone.created_at.desc()).all()
    return [milestone_read(row) for row in rows]


@milestones_router.post("", response_model=MilestoneRead)
def create_milestone(payload: MilestoneCreate, _: User = Depends(permission_dependency("milestones", "create")), db: Session = Depends(get_db)):
    if not db.get(Project, payload.project_id):
        raise HTTPException(status_code=400, detail="Project does not exist")
    data = payload.model_dump()
    ensure_end_date_after_start_date(data.get("start_date"), data.get("end_date"), "Milestone")
    row = Milestone(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return milestone_read(row)


@milestones_router.put("/{milestone_id}", response_model=MilestoneRead)
def update_milestone(milestone_id: UUID, payload: MilestoneUpdate, _: User = Depends(permission_dependency("milestones", "update")), db: Session = Depends(get_db)):
    row = db.get(Milestone, milestone_id)
    if not row:
        raise HTTPException(status_code=404, detail="Milestone not found")
    data = normalize_consultant_optional_fields(payload.model_dump(exclude_unset=True))
    if data.get("project_id") and not db.get(Project, data["project_id"]):
        raise HTTPException(status_code=400, detail="Project does not exist")
    target_start = data.get("start_date", row.start_date)
    target_end = data.get("end_date", row.end_date)
    ensure_end_date_after_start_date(target_start, target_end, "Milestone")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return milestone_read(row)


@milestones_router.delete("/{milestone_id}")
def delete_milestone(milestone_id: UUID, _: User = Depends(permission_dependency("milestones", "delete")), db: Session = Depends(get_db)):
    row = db.get(Milestone, milestone_id)
    if not row:
        raise HTTPException(status_code=404, detail="Milestone not found")
    db.delete(row)
    db.commit()
    return {"message": "Milestone deleted"}


@consultants_router.get("", response_model=list[ConsultantRead])
def list_consultants(_: User = Depends(permission_dependency("consultants", "read")), db: Session = Depends(get_db)):
    rows = db.query(Consultant).order_by(Consultant.created_at.desc()).all()
    return [consultant_read(row) for row in rows]




@consultants_router.patch("/recurring-invoices", response_model=list[ConsultantRead])
def update_recurring_consultants(payload: RecurringConsultantsUpdate, _: User = Depends(permission_dependency("consultants", "update")), db: Session = Depends(get_db)):
    selected_ids = set(payload.consultant_ids or [])
    rows = db.query(Consultant).all()
    for row in rows:
        row.is_recurring_invoice = row.id in selected_ids
    db.commit()
    rows = db.query(Consultant).order_by(Consultant.name.asc()).all()
    return [consultant_read(row) for row in rows]

@consultants_router.post("", response_model=ConsultantRead)
def create_consultant(payload: ConsultantCreate, _: User = Depends(permission_dependency("consultants", "create")), db: Session = Depends(get_db)):
    data = normalize_consultant_optional_fields(payload.model_dump())
    if data.get("project_id") and not db.get(Project, data["project_id"]):
        raise HTTPException(status_code=400, detail="Project does not exist")
    ensure_end_date_after_start_date(data.get("start_date"), data.get("end_date"), "Consultant")
    data["name"] = consultant_full_name(data)
    row = Consultant(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return consultant_read(row)


@consultants_router.put("/{consultant_id}", response_model=ConsultantRead)
def update_consultant(consultant_id: UUID, payload: ConsultantUpdate, _: User = Depends(permission_dependency("consultants", "update")), db: Session = Depends(get_db)):
    row = db.get(Consultant, consultant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Consultant not found")
    data = normalize_consultant_optional_fields(payload.model_dump(exclude_unset=True))
    if data.get("project_id") and not db.get(Project, data["project_id"]):
        raise HTTPException(status_code=400, detail="Project does not exist")
    target_start = data.get("start_date", row.start_date)
    target_end = data.get("end_date", row.end_date)
    ensure_end_date_after_start_date(target_start, target_end, "Consultant")
    if any(key in data for key in ["first_name", "last_name", "name"]):
        merged = {"first_name": row.first_name, "last_name": row.last_name, "name": row.name, **data}
        data["name"] = consultant_full_name(merged)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return consultant_read(row)


@consultants_router.delete("/{consultant_id}")
def delete_consultant(consultant_id: UUID, _: User = Depends(permission_dependency("consultants", "delete")), db: Session = Depends(get_db)):
    row = db.get(Consultant, consultant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Consultant not found")
    db.delete(row)
    db.commit()
    return {"message": "Consultant deleted"}
