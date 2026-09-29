"""Use cases: load state, apply domain rules, persist. Each function commits its own transaction."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from toollib import domain
from toollib.clock import AppClock
from toollib.errors import DomainError, NotFoundError
from toollib.models import Item, ItemStatus, Loan, Member
from toollib.schemas import ItemCreate, MemberCreate

# ---- items ---------------------------------------------------------------


def create_item(session: Session, clock: AppClock, data: ItemCreate) -> Item:
    item = Item(name=data.name, category=data.category, status=ItemStatus.AVAILABLE, created_at=clock.now())
    session.add(item)
    session.commit()
    return item


def list_items(session: Session, status: ItemStatus | None, category: str | None) -> list[Item]:
    query = select(Item).order_by(Item.id)
    if status is not None:
        query = query.where(Item.status == status)
    if category is not None:
        query = query.where(Item.category == category)
    return list(session.scalars(query))


def get_item(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise NotFoundError("ITEM_NOT_FOUND", f"Item {item_id} not found")
    return item


# ---- members -------------------------------------------------------------


def create_member(session: Session, clock: AppClock, data: MemberCreate) -> Member:
    email = data.email.lower()
    if session.scalar(select(Member).where(Member.email == email)) is not None:
        raise DomainError("EMAIL_TAKEN", "A member with this email already exists")
    member = Member(name=data.name, email=email, fees_owed_cents=0, created_at=clock.now())
    session.add(member)
    session.commit()
    return member


def get_member(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        raise NotFoundError("MEMBER_NOT_FOUND", f"Member {member_id} not found")
    return member


def pay_fees(session: Session, member_id: int, amount_cents: int) -> Member:
    member = get_member(session, member_id)
    if amount_cents > member.fees_owed_cents:
        raise DomainError("OVERPAYMENT", "Payment exceeds the fees owed")
    member.fees_owed_cents -= amount_cents
    session.commit()
    return member


# ---- loans ---------------------------------------------------------------


def borrow(session: Session, clock: AppClock, member_id: int, item_id: int) -> Loan:
    member = get_member(session, member_id)
    item = get_item(session, item_id)
    active_loans = session.scalar(
        select(func.count()).select_from(Loan).where(Loan.member_id == member.id, Loan.returned_at.is_(None))
    )
    domain.check_can_borrow(
        fees_owed_cents=member.fees_owed_cents,
        active_loans=active_loans or 0,
        item_available=item.status == ItemStatus.AVAILABLE,
    )

    now = clock.now()
    loan = Loan(item_id=item.id, member_id=member.id, borrowed_at=now, due_at=domain.due_date(now))
    item.status = ItemStatus.ON_LOAN
    session.add(loan)
    session.commit()
    return loan


def get_loan(session: Session, loan_id: int) -> Loan:
    loan = session.get(Loan, loan_id)
    if loan is None:
        raise NotFoundError("LOAN_NOT_FOUND", f"Loan {loan_id} not found")
    return loan


def list_loans(session: Session, member_id: int | None, active: bool | None) -> list[Loan]:
    query = select(Loan).order_by(Loan.id)
    if member_id is not None:
        query = query.where(Loan.member_id == member_id)
    if active is True:
        query = query.where(Loan.returned_at.is_(None))
    elif active is False:
        query = query.where(Loan.returned_at.is_not(None))
    return list(session.scalars(query))


def extend_loan(session: Session, clock: AppClock, loan_id: int) -> Loan:
    loan = get_loan(session, loan_id)
    domain.check_can_extend(
        returned=loan.returned_at is not None, extended=loan.extended, due_at=loan.due_at, now=clock.now()
    )
    loan.due_at = loan.due_at + domain.EXTENSION_PERIOD
    loan.extended = True
    session.commit()
    return loan


def return_loan(session: Session, clock: AppClock, loan_id: int) -> Loan:
    loan = get_loan(session, loan_id)
    if loan.returned_at is not None:
        raise DomainError("LOAN_ALREADY_RETURNED", "Loan has already been returned")

    now = clock.now()
    fee = domain.late_fee_cents(loan.due_at, now)
    loan.returned_at = now
    loan.late_fee_cents = fee
    get_member(session, loan.member_id).fees_owed_cents += fee
    get_item(session, loan.item_id).status = ItemStatus.AVAILABLE
    session.commit()
    return loan


# ---- test support --------------------------------------------------------


def reset_all(session: Session) -> None:
    for model in (Loan, Member, Item):  # children first, for foreign keys
        session.execute(delete(model))
    session.commit()
