from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from toollib.clock import AppClock
from toollib.schemas import ErrorResponse


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_clock(request: Request) -> AppClock:
    return request.app.state.clock


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[AppClock, Depends(get_clock)]


def error_responses(*status_codes: int) -> dict[int | str, dict]:
    """Documents our error shape in OpenAPI for the given status codes."""
    return {code: {"model": ErrorResponse} for code in status_codes}
