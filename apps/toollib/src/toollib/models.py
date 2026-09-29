from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from toollib.db import Base, UTCDateTime


class ItemStatus(StrEnum):
    AVAILABLE = "available"
    ON_LOAN = "on_loan"


class Category(StrEnum):
    POWER_TOOLS = "power_tools"
    HAND_TOOLS = "hand_tools"
    GARDEN = "garden"
    OUTDOOR = "outdoor"
    LADDERS = "ladders"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=ItemStatus.AVAILABLE)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-case (MEM-1)
    fees_owed_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    borrowed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    due_at: Mapped[datetime] = mapped_column(UTCDateTime)
    returned_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    extended: Mapped[bool] = mapped_column(default=False)
    late_fee_cents: Mapped[int] = mapped_column(default=0)
