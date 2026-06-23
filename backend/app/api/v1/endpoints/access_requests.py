from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, permission_dependency
from app.db.session import get_db
from app.models.access_request import AccessRequest
from app.models.client import Client
from app.models.client_access import UserClientAccess
from app.models.user import Module, Role, RoleModulePermission, User, UserRole
from app.schemas.access_request import AccessDecision, AccessRequestCreate, AccessRequestRead
from app.services.rbac import CRUD_ACTIONS, has_permission

router = APIRouter(prefix="/access-requests", tags=["access-requests"])


def to_access_request_read(db: Session, row: AccessRequest) -> AccessRequestRead:
    """Return access request with requester display details for admin UI."""
    requester = db.get(User, row.requester_id)
    return AccessRequestRead(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        requester_id=row.requester_id,
        requester_email=requester.email if requester else None,
        requester_name=requester.full_name if requester else None,
        module_code=row.module_code,
        requested_permission=row.requested_permission,
        reason=row.reason or "",
        client_id=row.client_id,
        status=row.status,
        decided_by_id=row.decided_by_id,
        rejection_reason=row.rejection_reason,
    )


@router.get("", response_model=list[AccessRequestRead])
def list_access_requests(current_user: User = Depends(permission_dependency("access_requests", "read")), db: Session = Depends(get_db)):
    """List access requests with proper visibility.

    Admin/superadmin users who can update access requests need to see every
    pending request so they can approve/reject them. Normal users should only
    see requests raised by themselves, otherwise one user can view another
    user's access history.
    """
    query = db.query(AccessRequest)
    if not current_user.is_superadmin and not has_permission(db, current_user, "access_requests", "update"):
        query = query.filter(AccessRequest.requester_id == current_user.id)

    rows = query.order_by(AccessRequest.created_at.desc()).all()
    return [to_access_request_read(db, row) for row in rows]




@router.get("/client-options")
def access_request_client_options(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Client/vendor list for access request forms.

    This endpoint intentionally needs only login, not client-module read access,
    so users can request invoice access for a specific client/vendor.
    """
    rows = db.query(Client).order_by(Client.name.asc()).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "label": row.name,
            "client_kind": row.client_kind,
        }
        for row in rows
    ]


@router.post("", response_model=AccessRequestRead)
def create_access_request(payload: AccessRequestCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a module-access request.

    Users cannot request the same module permission again when it is already
    granted, and they cannot create duplicate pending requests for the same
    module/permission/client combination.
    """
    module_code = payload.module_code.strip().lower()
    requested_permission = payload.requested_permission.strip().lower()
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reason is required")

    if requested_permission not in CRUD_ACTIONS:
        raise HTTPException(status_code=400, detail="Requested permission must be one of read, create, update, delete")

    module = db.query(Module).filter(Module.code == module_code).first()
    if not module:
        raise HTTPException(status_code=400, detail=f"Unknown module code: {module_code}")

    if payload.client_id and not db.get(Client, payload.client_id):
        raise HTTPException(status_code=400, detail="Client ID does not exist")

    # create/update/delete includes read. Do not let users request read when they
    # already have any stronger permission on the same module.
    if requested_permission == "read" and any(has_permission(db, current_user, module_code, action) for action in ("create", "update", "delete")):
        raise HTTPException(status_code=400, detail=f"You already have read access for {module_code} through create/update/delete permission")

    if has_permission(db, current_user, module_code, requested_permission):
        # For client-scoped invoice access, allow request if the user does not
        # already have that specific client assignment.
        if not (module_code == "invoices" and payload.client_id and requested_permission in {"create", "update", "delete"}):
            raise HTTPException(status_code=400, detail=f"You already have {requested_permission} access for {module_code}")

    if module_code == "invoices" and requested_permission in {"create", "update", "delete"} and payload.client_id:
        existing_client_access = db.get(UserClientAccess, {"user_id": current_user.id, "client_id": payload.client_id})
        if existing_client_access:
            raise HTTPException(status_code=400, detail="You already have invoice access for this client/vendor")

    existing_pending = (
        db.query(AccessRequest)
        .filter(
            AccessRequest.requester_id == current_user.id,
            AccessRequest.module_code == module_code,
            AccessRequest.requested_permission == requested_permission,
            AccessRequest.client_id == payload.client_id,
            AccessRequest.status == "pending",
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(status_code=400, detail=f"A pending request already exists for {module_code}:{requested_permission}")

    row = AccessRequest(
        requester_id=current_user.id,
        module_code=module_code,
        requested_permission=requested_permission,
        reason=reason,
        client_id=payload.client_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_access_request_read(db, row)


@router.put("/{request_id}/decision", response_model=AccessRequestRead)
def decide_access_request(
    request_id: UUID,
    payload: AccessDecision,
    current_user: User = Depends(permission_dependency("access_requests", "update")),
    db: Session = Depends(get_db),
):
    """Approve/reject access requests.

    Approval grants the requested permission via a system-generated role.
    If a client_id is present, approval also grants client-scoped access so HR
    can create invoices only for that approved client.
    """
    status = payload.status.strip().lower()
    if status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Status must be approved or rejected")

    row = db.get(AccessRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Access request not found")

    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be decided")

    if row.requested_permission not in CRUD_ACTIONS:
        raise HTTPException(status_code=400, detail="Requested permission must be one of read, create, update, delete")

    if status == "rejected":
        rejection_reason = (payload.rejection_reason or "").strip()
        if not rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        row.rejection_reason = rejection_reason

    if status == "approved":
        module = db.query(Module).filter(Module.code == row.module_code).first()
        if not module:
            raise HTTPException(status_code=400, detail=f"Unknown module code: {row.module_code}")

        requester = db.get(User, row.requester_id)
        if not requester:
            raise HTTPException(status_code=400, detail="Requester user not found")

        if row.client_id and not db.get(Client, row.client_id):
            raise HTTPException(status_code=400, detail="Client ID does not exist")

        if row.module_code == "invoices" and row.requested_permission in {"create", "update", "delete"} and row.client_id:
            existing_client_access = db.get(UserClientAccess, {"user_id": row.requester_id, "client_id": row.client_id})
            if not existing_client_access:
                db.add(UserClientAccess(user_id=row.requester_id, client_id=row.client_id))
        elif has_permission(db, requester, row.module_code, row.requested_permission):
            raise HTTPException(status_code=400, detail=f"Requester already has {row.requested_permission} access for {row.module_code}")

        role_name = f"access_{str(row.requester_id)[:8]}_{row.module_code}_{row.requested_permission}"
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description="System generated role from approved access request")
            db.add(role)
            db.flush()

        permission = db.query(RoleModulePermission).filter_by(role_id=role.id, module_id=module.id).first()
        if not permission:
            permission = RoleModulePermission(role_id=role.id, module_id=module.id)
            db.add(permission)

        permission.can_read = True
        setattr(permission, CRUD_ACTIONS[row.requested_permission], True)

        existing_user_role = db.query(UserRole).filter_by(user_id=row.requester_id, role_id=role.id).first()
        if not existing_user_role:
            db.add(UserRole(user_id=row.requester_id, role_id=role.id))

        row.rejection_reason = None

    row.status = status
    row.decided_by_id = current_user.id
    db.commit()
    db.refresh(row)
    return to_access_request_read(db, row)
