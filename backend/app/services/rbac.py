from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import Module, Role, RoleModulePermission, User, UserRole

CRUD_ACTIONS = {"read": "can_read", "create": "can_create", "update": "can_update", "delete": "can_delete"}
MODULES = [
    ("home", "Home"),
    ("users", "Users"),
    ("finance", "Finance"),
    ("hr", "HR"),
    ("invoices", "Invoice Generator"),
    ("companies", "Companies"),
    ("clients", "Clients"),
    ("projects", "Projects"),
    ("milestones", "Milestones"),
    ("consultants", "Consultants"),
    ("banks", "Bank Details"),
    ("access_requests", "Access Requests"),
]
ROLES = [
    ("admin", "Can manage users, clients, companies, projects, milestones, banks, invoices; cannot manage superadmin."),
    ("finance", "Finance team with default invoice read/create access."),
    ("hr", "HR team; can request invoice access."),
    ("bank_manager", "Can manage bank details."),
]
DEFAULT_PERMISSIONS = {
    "admin": {
        "home": "read",
        "users": "read,create,update,delete",
        "clients": "read,create,update,delete",
        "companies": "read,create,update,delete",
        "projects": "read,create,update,delete",
        "milestones": "read,create,update,delete",
        "consultants": "read,create,update,delete",
        "banks": "read,create,update,delete",
        "invoices": "read,create,update,delete",
        "access_requests": "read,update",
    },
    "finance": {
        "home": "read",
        "finance": "read",
        "users": "read",
        "clients": "read",
        "companies": "read",
        "projects": "read",
        "milestones": "read",
        "consultants": "read",
        "banks": "read",
        "invoices": "read,create",
        "access_requests": "read,create",
    },
    "hr": {
        "home": "read",
        "hr": "read",
        "consultants": "read,create,update,delete",
        "invoices": "read",
        "access_requests": "read,create",
    },
    "bank_manager": {
        "home": "read",
        "banks": "read,create,update,delete",
    },
}


def ensure_seed_data(db: Session) -> None:
    """Create base modules, roles and role permissions if missing."""
    for code, name in MODULES:
        if not db.query(Module).filter(Module.code == code).first():
            db.add(Module(code=code, name=name))
    for name, desc in ROLES:
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name, description=desc))
    db.commit()

    modules = {m.code: m for m in db.query(Module).all()}
    roles = {r.name: r for r in db.query(Role).all()}
    for role_name, module_map in DEFAULT_PERMISSIONS.items():
        role = roles[role_name]
        for module_code, actions_csv in module_map.items():
            module = modules[module_code]
            existing = db.query(RoleModulePermission).filter_by(role_id=role.id, module_id=module.id).first()
            actions = {x.strip() for x in actions_csv.split(",")}
            payload = {
                "can_read": "read" in actions,
                "can_create": "create" in actions,
                "can_update": "update" in actions,
                "can_delete": "delete" in actions,
            }
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
            else:
                db.add(RoleModulePermission(role_id=role.id, module_id=module.id, **payload))
    db.commit()


def get_user_roles(user: User) -> list[str]:
    return [ur.role.name for ur in user.roles]


def get_user_permissions(db: Session, user: User) -> list[dict]:
    if user.is_superadmin:
        return [{"module_code": m.code, "can_read": True, "can_create": True, "can_update": True, "can_delete": True} for m in db.query(Module).all()]

    role_ids = [ur.role_id for ur in user.roles]
    rows = db.query(RoleModulePermission).join(Module).filter(RoleModulePermission.role_id.in_(role_ids)).all()
    merged: dict[str, dict] = {}
    for row in rows:
        code = row.module.code
        current = merged.setdefault(code, {"module_code": code, "can_read": False, "can_create": False, "can_update": False, "can_delete": False})
        current["can_read"] = current["can_read"] or row.can_read
        current["can_create"] = current["can_create"] or row.can_create
        current["can_update"] = current["can_update"] or row.can_update
        current["can_delete"] = current["can_delete"] or row.can_delete

    # Business rule: create/update/delete includes read for the same module.
    # This prevents unnecessary read-access requests and lets users open modules
    # where they already have an operational permission.
    for current in merged.values():
        if current["can_create"] or current["can_update"] or current["can_delete"]:
            current["can_read"] = True
    return list(merged.values())


def has_permission(db: Session, user: User, module_code: str, action: str) -> bool:
    if user.is_superadmin:
        return True
    if action not in CRUD_ACTIONS:
        return False
    for permission in get_user_permissions(db, user):
        if permission["module_code"] == module_code and permission[CRUD_ACTIONS[action]]:
            return True
    return False


def require_permission(module_code: str, action: str):
    def dependency(current_user: User, db: Session):
        if not has_permission(db, current_user, module_code, action):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing {action} access for {module_code}")
        return current_user
    return dependency


def assign_roles_to_user(db: Session, user: User, role_names: list[str]) -> User:
    roles = db.query(Role).filter(Role.name.in_(role_names)).all() if role_names else []
    found = {r.name for r in roles}
    missing = set(role_names) - found
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown role(s): {', '.join(sorted(missing))}")
    user.roles.clear()
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    return user
