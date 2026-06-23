from uuid import UUID

from app.schemas.common import IDModel


class ModuleDocumentRead(IDModel):
    module_code: str
    record_id: UUID
    original_filename: str
    stored_filename: str
    content_type: str | None = None
    notes: str | None = None
