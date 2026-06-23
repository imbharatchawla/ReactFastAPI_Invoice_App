from pydantic import BaseModel, Field

from app.schemas.common import IDModel


class BankAccountCreate(BaseModel):
    account_holder_name: str = Field(min_length=2)
    bank_name: str = Field(min_length=2)
    account_number: str = Field(min_length=4)
    country: str = "India"
    currency: str = "INR"
    ifsc_code: str | None = None
    swift_code: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    branch_address: str | None = None
    notes: str | None = None


class BankAccountUpdate(BaseModel):
    account_holder_name: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    country: str | None = None
    currency: str | None = None
    ifsc_code: str | None = None
    swift_code: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    branch_address: str | None = None
    notes: str | None = None


class BankAccountRead(IDModel):
    account_holder_name: str
    bank_name: str
    account_number: str
    country: str
    currency: str
    ifsc_code: str | None = None
    swift_code: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    branch_address: str | None = None
    notes: str | None = None
