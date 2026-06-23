from app.models.base import Base  # Alembic metadata base
# Import all SQLAlchemy models here so Alembic can detect them.
from app.models.user import User, Role, Module, UserRole, RoleModulePermission  # noqa: F401
from app.models.catalog import Company, Project, Milestone, Consultant  # noqa: F401
from app.models.client import Client, VendorInvoice  # noqa: F401
from app.models.bank import BankAccount  # noqa: F401
from app.models.invoice import Invoice, InvoiceRevertRequest, InvoiceFinalizationRequest  # noqa: F401
from app.models.access_request import AccessRequest  # noqa: F401
from app.models.client_access import UserClientAccess  # noqa: F401

from app.models.document import ModuleDocument  # noqa: F401

from app.models.forgot_password import ForgotPasswordRequest  # noqa: F401
