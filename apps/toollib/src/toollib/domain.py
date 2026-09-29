"""Pure business rules: no database, no HTTP. Rule IDs refer to docs/domain.md."""

from datetime import datetime, timedelta

from toollib.errors import DomainError

LOAN_PERIOD = timedelta(days=7)  # LOAN-4
EXTENSION_PERIOD = timedelta(days=7)  # EXT-4
MAX_ACTIVE_LOANS = 3  # LOAN-2
BLOCK_THRESHOLD_CENTS = 1000  # LOAN-3
LATE_FEE_PER_DAY_CENTS = 100  # RET-3
LATE_FEE_CAP_CENTS = 2000  # RET-4


def due_date(borrowed_at: datetime) -> datetime:
    return borrowed_at + LOAN_PERIOD


def is_blocked(fees_owed_cents: int) -> bool:
    return fees_owed_cents > BLOCK_THRESHOLD_CENTS


def late_fee_cents(due_at: datetime, returned_at: datetime) -> int:
    """100 cents per started day late, capped at 2000 (RET-3, RET-4)."""
    if returned_at <= due_at:
        return 0
    full_days, remainder = divmod(returned_at - due_at, timedelta(days=1))
    started_days = full_days + (1 if remainder else 0)
    return min(started_days * LATE_FEE_PER_DAY_CENTS, LATE_FEE_CAP_CENTS)


def check_can_borrow(*, fees_owed_cents: int, active_loans: int, item_available: bool) -> None:
    """Checked in the order given by LOAN-6."""
    if is_blocked(fees_owed_cents):
        raise DomainError("MEMBER_BLOCKED", "Member owes more than EUR 10.00 in fees")
    if active_loans >= MAX_ACTIVE_LOANS:
        raise DomainError("LOAN_LIMIT_REACHED", f"Member already has {MAX_ACTIVE_LOANS} active loans")
    if not item_available:
        raise DomainError("ITEM_NOT_AVAILABLE", "Item is not available")


def check_can_extend(*, returned: bool, extended: bool, due_at: datetime, now: datetime) -> None:
    if returned:
        raise DomainError("LOAN_ALREADY_RETURNED", "Loan has already been returned")
    if extended:
        raise DomainError("EXTENSION_NOT_ALLOWED", "Loan has already been extended")
    if now > due_at:
        raise DomainError("EXTENSION_NOT_ALLOWED", "Overdue loans cannot be extended")
