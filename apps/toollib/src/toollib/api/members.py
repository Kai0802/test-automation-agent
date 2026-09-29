from fastapi import APIRouter, status

from toollib import services
from toollib.api.deps import ClockDep, SessionDep, error_responses
from toollib.schemas import MemberCreate, MemberOut, PaymentCreate

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", status_code=status.HTTP_201_CREATED, responses=error_responses(409, 422))
def create_member(data: MemberCreate, session: SessionDep, clock: ClockDep) -> MemberOut:
    """Register a member. Emails are unique, case-insensitive (MEM-1)."""
    return MemberOut.model_validate(services.create_member(session, clock, data))


@router.get("/{member_id}", responses=error_responses(404))
def get_member(member_id: int, session: SessionDep) -> MemberOut:
    return MemberOut.model_validate(services.get_member(session, member_id))


@router.post("/{member_id}/payments", responses=error_responses(404, 409, 422))
def pay_fees(member_id: int, data: PaymentCreate, session: SessionDep) -> MemberOut:
    """Pay off late fees. Cannot pay more than is owed (PAY-2)."""
    return MemberOut.model_validate(services.pay_fees(session, member_id, data.amount_cents))
