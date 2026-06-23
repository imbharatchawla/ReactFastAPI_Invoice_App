from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import permission_dependency
from app.db.session import get_db
from app.models.bank import BankAccount
from app.models.user import User
from app.schemas.bank import BankAccountCreate, BankAccountRead, BankAccountUpdate

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("", response_model=list[BankAccountRead])
def list_banks(_: User = Depends(permission_dependency("banks", "read")), db: Session = Depends(get_db)):
    return db.query(BankAccount).order_by(BankAccount.created_at.desc()).all()


@router.post("", response_model=BankAccountRead)
def create_bank(payload: BankAccountCreate, _: User = Depends(permission_dependency("banks", "create")), db: Session = Depends(get_db)):
    bank = BankAccount(**payload.model_dump())
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@router.put("/{bank_id}", response_model=BankAccountRead)
def update_bank(bank_id: UUID, payload: BankAccountUpdate, _: User = Depends(permission_dependency("banks", "update")), db: Session = Depends(get_db)):
    bank = db.get(BankAccount, bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(bank, key, value)
    db.commit()
    db.refresh(bank)
    return bank


@router.delete("/{bank_id}")
def delete_bank(bank_id: UUID, _: User = Depends(permission_dependency("banks", "delete")), db: Session = Depends(get_db)):
    bank = db.get(BankAccount, bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank account not found")
    db.delete(bank)
    db.commit()
    return {"message": "Bank account deleted"}
