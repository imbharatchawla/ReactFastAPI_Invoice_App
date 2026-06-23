from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDModel(ORMBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
