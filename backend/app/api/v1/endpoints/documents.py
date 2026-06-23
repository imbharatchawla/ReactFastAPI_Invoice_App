from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.document import ModuleDocument
from app.models.user import User
from app.schemas.document import ModuleDocumentRead
from app.services.rbac import has_permission

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "module_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

VALID_MODULES = {"companies", "clients", "projects", "milestones", "consultants", "banks", "invoices", "invoice_generated", "users", "access_requests"}
MODULE_PERMISSION_MAP = {"invoice_generated": "invoices"}


def effective_module(module_code: str) -> str:
    return MODULE_PERMISSION_MAP.get(module_code, module_code)


def ensure_module(module_code: str) -> None:
    if module_code not in VALID_MODULES:
        raise HTTPException(status_code=400, detail="Invalid module")


def is_admin_user(user: User) -> bool:
    return bool(user.is_superadmin or any(ur.role and ur.role.name == "admin" for ur in user.roles))


def require_module_permission(db: Session, user: User, module_code: str, action: str) -> None:
    target = effective_module(module_code)
    if not has_permission(db, user, target, action):
        raise HTTPException(status_code=403, detail=f"Missing {action} access for {target}")


def to_read(row: ModuleDocument) -> ModuleDocumentRead:
    return ModuleDocumentRead.model_validate(row)


@router.get("/{module_code}/{record_id}", response_model=list[ModuleDocumentRead])
def list_documents(module_code: str, record_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_module(module_code)
    require_module_permission(db, current_user, module_code, "read")
    rows = db.query(ModuleDocument).filter(ModuleDocument.module_code == module_code, ModuleDocument.record_id == record_id).order_by(ModuleDocument.created_at.desc()).all()
    return [to_read(row) for row in rows]


@router.post("/{module_code}/{record_id}", response_model=ModuleDocumentRead)
async def upload_document(module_code: str, record_id: UUID, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_module(module_code)
    require_module_permission(db, current_user, module_code, "create")
    suffix = Path(file.filename or "document").suffix
    safe_module = module_code.replace("/", "_")
    stored_name = f"{safe_module}_{record_id}_{uuid4().hex}{suffix}"
    target_path = UPLOAD_DIR / stored_name
    content = await file.read()
    target_path.write_bytes(content)
    row = ModuleDocument(module_code=module_code, record_id=record_id, original_filename=file.filename or stored_name, stored_filename=stored_name, file_path=str(target_path), content_type=file.content_type)
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_read(row)


@router.get("/{module_code}/{record_id}/{document_id}/download")
def download_document(module_code: str, record_id: UUID, document_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_module(module_code)
    require_module_permission(db, current_user, module_code, "read")
    row = db.get(ModuleDocument, document_id)
    if not row or row.module_code != module_code or row.record_id != record_id:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file missing on server")
    return FileResponse(path, filename=row.original_filename, media_type=row.content_type or "application/octet-stream")


@router.delete("/{module_code}/{record_id}/{document_id}")
def delete_document(module_code: str, record_id: UUID, document_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_module(module_code)
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Only admin or superadmin can delete uploaded documents")
    row = db.get(ModuleDocument, document_id)
    if not row or row.module_code != module_code or row.record_id != record_id:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(row.file_path)
    db.delete(row)
    db.commit()
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    return {"message": "Document deleted"}
