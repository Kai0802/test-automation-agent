import itertools
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from toollib.clock import AppClock
from toollib.config import Settings
from toollib.main import create_app

START = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)  # a Monday, 10:00 UTC


class Api:
    """Thin helpers over the HTTP API so tests read as scenarios."""

    def __init__(self, client: TestClient, clock: AppClock) -> None:
        self.client = client
        self.clock = clock
        self._emails = itertools.count(1)

    def item(self, name: str = "Cordless drill", category: str = "power_tools") -> dict[str, Any]:
        response = self.client.post("/items", json={"name": name, "category": category})
        assert response.status_code == 201, response.text
        return response.json()

    def member(self, name: str = "Alex Kim", email: str | None = None) -> dict[str, Any]:
        email = email or f"member{next(self._emails)}@example.com"
        response = self.client.post("/members", json={"name": name, "email": email})
        assert response.status_code == 201, response.text
        return response.json()

    def borrow(self, member_id: int, item_id: int) -> dict[str, Any]:
        response = self.client.post("/loans", json={"member_id": member_id, "item_id": item_id})
        assert response.status_code == 201, response.text
        return response.json()

    def return_loan(self, loan_id: int) -> dict[str, Any]:
        response = self.client.post(f"/loans/{loan_id}/return")
        assert response.status_code == 200, response.text
        return response.json()

    def get_member(self, member_id: int) -> dict[str, Any]:
        return self.client.get(f"/members/{member_id}").json()

    def advance(self, **kwargs: float) -> None:
        self.clock.advance(timedelta(**kwargs))

    def owe(self, member_id: int, cents: int) -> None:
        """Give a member a fee balance by returning a loan late. `cents` must be a multiple of 100, max 2000."""
        loan = self.borrow(member_id, self.item()["id"])
        self.advance(days=7, seconds=(cents // 100 - 1) * 86400 + 1)
        assert self.return_loan(loan["id"])["late_fee_cents"] == cents


@pytest.fixture
def clock() -> AppClock:
    clock = AppClock()
    clock.freeze(START)
    return clock


@pytest.fixture
def client(clock: AppClock) -> Iterator[TestClient]:
    app = create_app(Settings(database_url="sqlite://", test_mode=True), clock=clock)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api(client: TestClient, clock: AppClock) -> Api:
    return Api(client, clock)
