from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from toollib.models import Category, ItemStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ErrorBody(BaseModel):
    code: str = Field(examples=["ITEM_NOT_AVAILABLE"])
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ItemCreate(BaseModel):
    name: Name = Field(examples=["Cordless drill"])
    category: Category


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: Category
    status: ItemStatus
    created_at: datetime


class MemberCreate(BaseModel):
    name: Name = Field(examples=["Alex Kim"])
    email: EmailStr


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    fees_owed_cents: int
    created_at: datetime


class PaymentCreate(BaseModel):
    amount_cents: int = Field(gt=0, examples=[500])


class LoanCreate(BaseModel):
    item_id: int
    member_id: int


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    member_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    extended: bool
    late_fee_cents: int


class ClockSet(BaseModel):
    now: AwareDatetime


class ClockAdvance(BaseModel):
    seconds: int = Field(ge=0)


class ClockOut(BaseModel):
    now: datetime
