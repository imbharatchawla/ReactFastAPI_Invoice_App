from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import IDModel


class RoleRead(IDModel):
    name: str
    description: str | None = None


class UserCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "hr.user@example.com",
                "full_name": "HR User",
                "password": "Mahakal@777",
                "role_names": ["hr"],
            }
        }
    )

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_names: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role_names: list[str] | None = None


class UserRead(IDModel):
    email: EmailStr
    full_name: str
    is_active: bool
    is_superadmin: bool
    roles: list[str] = []


class AssignRoles(BaseModel):
    role_names: list[str]


class PermissionRead(BaseModel):
    module_code: str
    can_read: bool
    can_create: bool
    can_update: bool
    can_delete: bool


class MeResponse(UserRead):
    permissions: list[PermissionRead] = []
