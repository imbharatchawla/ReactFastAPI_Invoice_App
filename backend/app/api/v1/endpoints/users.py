from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import permission_dependency
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.client_access import UserClientAccess
from app.schemas.user import AssignRoles, UserCreate, UserRead, UserUpdate
from app.services.rbac import assign_roles_to_user, get_user_roles

router = APIRouter(prefix="/users", tags=["users"])


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superadmin=user.is_superadmin,
        roles=get_user_roles(user),
    )


@router.get("", response_model=list[UserRead])
def list_users(_: User = Depends(permission_dependency("users", "read")), db: Session = Depends(get_db)):
    return [to_user_read(u) for u in db.query(User).order_by(User.created_at.desc()).all()]


@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, current_user: User = Depends(permission_dependency("users", "create")), db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    role_names = [r.strip().lower() for r in payload.role_names if r and r.strip()]

    if "superadmin" in role_names:
        raise HTTPException(status_code=400, detail="Superadmin cannot be assigned as a normal role")
    if not current_user.is_superadmin and "admin" in role_names:
        raise HTTPException(status_code=403, detail="Only superadmin can create admin users")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(email=email, full_name=payload.full_name.strip(), hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.flush()
    assign_roles_to_user(db, user, role_names)
    db.refresh(user)
    return to_user_read(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, current_user: User = Depends(permission_dependency("users", "update")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Admin cannot modify superadmin")
    for field in ["full_name", "is_active"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(user)
    if payload.role_names is not None:
        role_names = [r.strip().lower() for r in payload.role_names if r and r.strip()]
        if "superadmin" in role_names:
            raise HTTPException(status_code=400, detail="Superadmin cannot be assigned as a normal role")
        if not current_user.is_superadmin and "admin" in role_names:
            raise HTTPException(status_code=403, detail="Only superadmin can assign admin role")
        assign_roles_to_user(db, user, role_names)
    return to_user_read(user)


@router.post("/{user_id}/roles", response_model=UserRead)
def assign_roles(user_id: UUID, payload: AssignRoles, current_user: User = Depends(permission_dependency("users", "update")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Admin cannot modify superadmin roles")
    role_names = [r.strip().lower() for r in payload.role_names if r and r.strip()]
    if "superadmin" in role_names:
        raise HTTPException(status_code=400, detail="Superadmin cannot be assigned as a normal role")
    if not current_user.is_superadmin and "admin" in role_names:
        raise HTTPException(status_code=403, detail="Only superadmin can assign admin role")
    return to_user_read(assign_roles_to_user(db, user, role_names))


@router.post("/{user_id}/revoke-access", response_model=UserRead)
def revoke_user_access(user_id: UUID, current_user: User = Depends(permission_dependency("users", "update")), db: Session = Depends(get_db)):
    """Remove all role/module/client-scoped access from a user without deleting the user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot revoke your own access")
    if user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin access cannot be revoked")
    target_roles = get_user_roles(user)
    if "admin" in target_roles and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can revoke admin access")
    db.query(UserRole).filter(UserRole.user_id == user.id).delete(synchronize_session=False)
    db.query(UserClientAccess).filter(UserClientAccess.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(user_id: UUID, current_user: User = Depends(permission_dependency("users", "update")), db: Session = Depends(get_db)):
    """Deactivate a user so further API calls fail and frontend logs them out on next action."""
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can deactivate users")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    if user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin cannot be deactivated")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.post("/{user_id}/activate", response_model=UserRead)
def activate_user(user_id: UUID, current_user: User = Depends(permission_dependency("users", "update")), db: Session = Depends(get_db)):
    """Reactivate a previously deactivated user."""
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can activate users")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin cannot be changed here")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return to_user_read(user)


@router.delete("/{user_id}")
def delete_user(user_id: UUID, current_user: User = Depends(permission_dependency("users", "delete")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Admin cannot delete superadmin")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
