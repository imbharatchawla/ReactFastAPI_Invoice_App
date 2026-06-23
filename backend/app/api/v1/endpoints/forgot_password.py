import random
import string
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.forgot_password import ForgotPasswordRequest
from app.models.user import User
from app.schemas.forgot_password import ForgotPasswordCreate, ForgotPasswordDecision, ForgotPasswordRead, ForgotPasswordRecoverResponse
from app.services.rbac import get_user_roles, has_permission

router = APIRouter(prefix="/forgot-password-requests", tags=["forgot-password-requests"])


def is_admin_user(db: Session, user: User) -> bool:
    return bool(user.is_superadmin or "admin" in get_user_roles(user) or has_permission(db, user, "access_requests", "update"))


def to_read(db: Session, row: ForgotPasswordRequest) -> ForgotPasswordRead:
    requester = db.get(User, row.user_id)
    return ForgotPasswordRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        email=row.email,
        requester_name=requester.full_name if requester else None,
        status=row.status,
        decided_by_id=row.decided_by_id,
    )


def generate_password() -> str:
    # Criteria-friendly temporary password: upper, lower, digit and special char.
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("@#$%&*!")
    rest = [random.choice(string.ascii_letters + string.digits) for _ in range(8)]
    chars = [upper, lower, digit, special, *rest]
    random.shuffle(chars)
    return "".join(chars)


@router.post("/public")
def create_forgot_password_request(payload: ForgotPasswordCreate, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No registered user found with this email")

    existing = (
        db.query(ForgotPasswordRequest)
        .filter(ForgotPasswordRequest.user_id == user.id, ForgotPasswordRequest.status == "pending")
        .first()
    )
    if not existing:
        db.add(ForgotPasswordRequest(user_id=user.id, email=email))
        db.commit()

    return {"message": "If this email is registered, admin will contact you."}


@router.get("", response_model=list[ForgotPasswordRead])
def list_forgot_password_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin_user(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    rows = db.query(ForgotPasswordRequest).order_by(ForgotPasswordRequest.created_at.desc()).all()
    return [to_read(db, row) for row in rows]


@router.put("/{request_id}/decision")
def decide_forgot_password_request(
    request_id: UUID,
    payload: ForgotPasswordDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_admin_user(db, current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    action = payload.action.strip().lower()
    if action not in {"recover", "decline"}:
        raise HTTPException(status_code=400, detail="Action must be recover or decline")

    row = db.get(ForgotPasswordRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Forgot password request not found")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be decided")

    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Requester user not found")

    row.decided_by_id = current_user.id
    if action == "decline":
        row.status = "declined"
        db.commit()
        db.refresh(row)
        return to_read(db, row)

    temporary_password = generate_password()
    user.hashed_password = get_password_hash(temporary_password)
    row.status = "recovered"
    db.commit()
    db.refresh(row)
    return ForgotPasswordRecoverResponse(id=row.id, email=row.email, status=row.status, temporary_password=temporary_password)
