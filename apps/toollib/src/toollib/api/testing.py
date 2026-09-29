"""Test-only endpoints (TEST-1 to TEST-3). Mounted only when TOOLLIB_TEST_MODE=true."""

from datetime import timedelta

from fastapi import APIRouter, status

from toollib import services
from toollib.api.deps import ClockDep, SessionDep
from toollib.schemas import ClockAdvance, ClockOut, ClockSet

router = APIRouter(prefix="/__test__", tags=["test support"])


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset(session: SessionDep, clock: ClockDep) -> None:
    services.reset_all(session)
    clock.unfreeze()


@router.post("/clock")
def set_clock(data: ClockSet, clock: ClockDep) -> ClockOut:
    clock.freeze(data.now)
    return ClockOut(now=clock.now())


@router.post("/clock/advance")
def advance_clock(data: ClockAdvance, clock: ClockDep) -> ClockOut:
    clock.advance(timedelta(seconds=data.seconds))
    return ClockOut(now=clock.now())
