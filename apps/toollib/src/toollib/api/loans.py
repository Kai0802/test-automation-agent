from fastapi import APIRouter, status

from toollib import services
from toollib.api.deps import ClockDep, SessionDep, error_responses
from toollib.schemas import LoanCreate, LoanOut

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", status_code=status.HTTP_201_CREATED, responses=error_responses(404, 409, 422))
def borrow(data: LoanCreate, session: SessionDep, clock: ClockDep) -> LoanOut:
    """Borrow an item for 7 days (LOAN-1 to LOAN-6)."""
    return LoanOut.model_validate(services.borrow(session, clock, data.member_id, data.item_id))


@router.get("")
def list_loans(session: SessionDep, member_id: int | None = None, active: bool | None = None) -> list[LoanOut]:
    """List loans. `active=true` means not yet returned."""
    return [LoanOut.model_validate(loan) for loan in services.list_loans(session, member_id, active)]


@router.get("/{loan_id}", responses=error_responses(404))
def get_loan(loan_id: int, session: SessionDep) -> LoanOut:
    return LoanOut.model_validate(services.get_loan(session, loan_id))


@router.post("/{loan_id}/extend", responses=error_responses(404, 409))
def extend_loan(loan_id: int, session: SessionDep, clock: ClockDep) -> LoanOut:
    """Extend once by 7 days, only if not overdue (EXT-1 to EXT-4)."""
    return LoanOut.model_validate(services.extend_loan(session, clock, loan_id))


@router.post("/{loan_id}/return", responses=error_responses(404, 409))
def return_loan(loan_id: int, session: SessionDep, clock: ClockDep) -> LoanOut:
    """Return an item. Late returns are charged 100 cents per started day, max 2000 (RET-1 to RET-5)."""
    return LoanOut.model_validate(services.return_loan(session, clock, loan_id))
