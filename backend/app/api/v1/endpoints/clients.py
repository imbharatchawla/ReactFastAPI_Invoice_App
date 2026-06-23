from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import permission_dependency
from app.db.session import get_db
from app.models.catalog import Company, Milestone, Project
from app.models.client import Client, VendorInvoice
from app.models.bank import BankAccount
from app.models.user import User
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate, VendorInvoiceRead

router = APIRouter(prefix="/clients", tags=["clients"])

UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "vendor_invoices"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def serialize_countries(value: list[str] | None) -> str | None:
    if not value:
        return None
    return ",".join([x.strip() for x in value if x and x.strip()])


def deserialize_countries(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [x.strip() for x in value.split(",") if x.strip()]


def normalize_payload(payload: dict) -> dict:
    if "countries" in payload:
        payload["countries"] = serialize_countries(payload.get("countries"))
        countries = deserialize_countries(payload.get("countries")) or []
        payload["country"] = countries[0] if countries else None
    if payload.get("client_kind"):
        payload["client_kind"] = str(payload["client_kind"]).strip().lower()
    return payload


def validate_client_mappings(db: Session, company_id=None, project_id=None, milestone_id=None, bank_account_id=None) -> None:
    if company_id and not db.get(Company, company_id):
        raise HTTPException(status_code=400, detail="Company does not exist")
    project = db.get(Project, project_id) if project_id else None
    if project_id and not project:
        raise HTTPException(status_code=400, detail="Project does not exist")
    milestone = db.get(Milestone, milestone_id) if milestone_id else None
    if milestone_id and not milestone:
        raise HTTPException(status_code=400, detail="Milestone does not exist")
    if milestone and project_id and milestone.project_id != project_id:
        raise HTTPException(status_code=400, detail="Milestone is not mapped to the selected project")
    if bank_account_id and not db.get(BankAccount, bank_account_id):
        raise HTTPException(status_code=400, detail="Bank account does not exist")


def to_client_read(row: Client) -> ClientRead:
    return ClientRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        name=row.name,
        client_kind=row.client_kind or "client",
        email=row.email,
        phone=row.phone,
        country=row.country,
        countries=deserialize_countries(row.countries),
        currency=row.currency,
        tax_id=row.tax_id,
        client_type=row.client_type,
        details=row.details,
        billing_address=row.billing_address,
        notes=row.notes,
        company_id=row.company_id,
        company_name=row.company.name if row.company else None,
        project_id=row.project_id,
        project_name=row.project.name if row.project else None,
        milestone_id=row.milestone_id,
        milestone_name=row.milestone.name if row.milestone else None,
        bank_account_id=row.bank_account_id,
        bank_account_label=f"{row.bank_account.bank_name} - {row.bank_account.account_holder_name}" if row.bank_account else None,
    )


def vendor_invoice_read(row: VendorInvoice) -> VendorInvoiceRead:
    return VendorInvoiceRead.model_validate(row)


@router.get("", response_model=list[ClientRead])
def list_clients(_: User = Depends(permission_dependency("clients", "read")), db: Session = Depends(get_db)):
    rows = db.query(Client).order_by(Client.created_at.desc()).all()
    return [to_client_read(row) for row in rows]


@router.post("", response_model=ClientRead)
def create_client(payload: ClientCreate, _: User = Depends(permission_dependency("clients", "create")), db: Session = Depends(get_db)):
    data = normalize_payload(payload.model_dump())
    validate_client_mappings(db, data.get("company_id"), data.get("project_id"), data.get("milestone_id"), data.get("bank_account_id"))
    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return to_client_read(client)


@router.put("/{client_id}", response_model=ClientRead)
def update_client(client_id: UUID, payload: ClientUpdate, _: User = Depends(permission_dependency("clients", "update")), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    data = normalize_payload(payload.model_dump(exclude_unset=True))
    validate_client_mappings(
        db,
        data.get("company_id", client.company_id),
        data.get("project_id", client.project_id),
        data.get("milestone_id", client.milestone_id),
        data.get("bank_account_id", client.bank_account_id),
    )
    for key, value in data.items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return to_client_read(client)


@router.delete("/{client_id}")
def delete_client(client_id: UUID, _: User = Depends(permission_dependency("clients", "delete")), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"message": "Client deleted"}


@router.get("/{client_id}/vendor-invoices", response_model=list[VendorInvoiceRead])
def list_vendor_invoices(client_id: UUID, _: User = Depends(permission_dependency("clients", "read")), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client/Vendor not found")
    rows = db.query(VendorInvoice).filter(VendorInvoice.client_id == client_id).order_by(VendorInvoice.created_at.desc()).all()
    return [vendor_invoice_read(row) for row in rows]


@router.post("/{client_id}/vendor-invoices", response_model=VendorInvoiceRead)
async def upload_vendor_invoice(
    client_id: UUID,
    file: UploadFile = File(...),
    _: User = Depends(permission_dependency("clients", "create")),
    db: Session = Depends(get_db),
):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client/Vendor not found")
    if (client.client_kind or "client").lower() != "vendor":
        raise HTTPException(status_code=400, detail="Vendor invoice upload is allowed only for vendor records")
    suffix = Path(file.filename or "invoice").suffix
    stored_name = f"{client_id}_{uuid4().hex}{suffix}"
    target_path = UPLOAD_DIR / stored_name
    content = await file.read()
    target_path.write_bytes(content)
    row = VendorInvoice(
        client_id=client_id,
        original_filename=file.filename or stored_name,
        stored_filename=stored_name,
        file_path=str(target_path),
        content_type=file.content_type,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return vendor_invoice_read(row)


@router.get("/{client_id}/vendor-invoices/{invoice_id}/download")
def download_vendor_invoice(
    client_id: UUID,
    invoice_id: UUID,
    _: User = Depends(permission_dependency("clients", "read")),
    db: Session = Depends(get_db),
):
    row = db.get(VendorInvoice, invoice_id)
    if not row or row.client_id != client_id:
        raise HTTPException(status_code=404, detail="Vendor invoice file not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Vendor invoice file missing on server")
    return FileResponse(path, filename=row.original_filename, media_type=row.content_type or "application/octet-stream")
