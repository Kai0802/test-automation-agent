from datetime import UTC, datetime, timedelta

import pytest

from toollib import domain
from toollib.errors import DomainError

DUE = datetime(2026, 1, 12, 10, 0, tzinfo=UTC)
DAY = timedelta(days=1)
SECOND = timedelta(seconds=1)


def test_due_date_is_seven_days_after_borrowing() -> None:  # LOAN-4
    assert domain.due_date(DUE - 7 * DAY) == DUE


@pytest.mark.parametrize(
    ("returned_at", "expected"),
    [
        (DUE - DAY, 0),  # early
        (DUE, 0),  # exactly on time
        (DUE + SECOND, 100),  # one second late starts a day
        (DUE + DAY, 100),  # exactly one full day late
        (DUE + DAY + SECOND, 200),  # starts the second day
        (DUE + 19 * DAY, 1900),
        (DUE + 20 * DAY, 2000),  # reaches the cap
        (DUE + 45 * DAY, 2000),  # stays capped
    ],
)
def test_late_fee(returned_at: datetime, expected: int) -> None:  # RET-3, RET-4
    assert domain.late_fee_cents(DUE, returned_at) == expected


@pytest.mark.parametrize(("owed", "blocked"), [(0, False), (1000, False), (1001, True)])
def test_block_threshold(owed: int, blocked: bool) -> None:  # LOAN-3
    assert domain.is_blocked(owed) is blocked


def test_can_borrow_when_all_rules_pass() -> None:
    domain.check_can_borrow(fees_owed_cents=1000, active_loans=2, item_available=True)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"fees_owed_cents": 1001, "active_loans": 0, "item_available": True}, "MEMBER_BLOCKED"),
        ({"fees_owed_cents": 0, "active_loans": 3, "item_available": True}, "LOAN_LIMIT_REACHED"),
        ({"fees_owed_cents": 0, "active_loans": 0, "item_available": False}, "ITEM_NOT_AVAILABLE"),
        # LOAN-6: when everything fails, the checks run in a fixed order
        ({"fees_owed_cents": 5000, "active_loans": 3, "item_available": False}, "MEMBER_BLOCKED"),
        ({"fees_owed_cents": 0, "active_loans": 3, "item_available": False}, "LOAN_LIMIT_REACHED"),
    ],
)
def test_borrow_rejections(kwargs: dict, code: str) -> None:
    with pytest.raises(DomainError) as exc:
        domain.check_can_borrow(**kwargs)
    assert exc.value.code == code


def test_can_extend_on_the_due_date() -> None:  # EXT-2: only *after* due_at is overdue
    domain.check_can_extend(returned=False, extended=False, due_at=DUE, now=DUE)


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"returned": True, "extended": False, "now": DUE - DAY}, "LOAN_ALREADY_RETURNED"),  # EXT-3
        ({"returned": False, "extended": True, "now": DUE - DAY}, "EXTENSION_NOT_ALLOWED"),  # EXT-1
        ({"returned": False, "extended": False, "now": DUE + SECOND}, "EXTENSION_NOT_ALLOWED"),  # EXT-2
    ],
)
def test_extend_rejections(kwargs: dict, code: str) -> None:
    with pytest.raises(DomainError) as exc:
        domain.check_can_extend(due_at=DUE, **kwargs)
    assert exc.value.code == code
