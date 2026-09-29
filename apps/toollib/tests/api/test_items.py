import pytest

from conftest import Api


def test_create_item_starts_available(api: Api) -> None:  # ITEM-1
    response = api.client.post("/items", json={"name": "  Ladder 3m  ", "category": "ladders"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ladder 3m"  # ITEM-2: trimmed
    assert body["category"] == "ladders"
    assert body["status"] == "available"
    assert body["created_at"] == "2026-01-05T10:00:00Z"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "category": "garden"},
        {"name": "   ", "category": "garden"},
        {"name": "x" * 101, "category": "garden"},
        {"name": "Rake", "category": "kitchen"},  # ITEM-3
        {"category": "garden"},
    ],
)
def test_create_item_validation(api: Api, payload: dict) -> None:  # ITEM-2, ITEM-3
    response = api.client.post("/items", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_name_of_exactly_100_characters_is_allowed(api: Api) -> None:  # ITEM-2
    assert api.client.post("/items", json={"name": "x" * 100, "category": "garden"}).status_code == 201


def test_filter_items_by_status_and_category(api: Api) -> None:  # ITEM-4
    drill = api.item("Drill", "power_tools")
    saw = api.item("Saw", "power_tools")
    api.item("Rake", "garden")
    api.borrow(api.member()["id"], drill["id"])

    available_power = api.client.get("/items", params={"status": "available", "category": "power_tools"}).json()
    on_loan = api.client.get("/items", params={"status": "on_loan"}).json()

    assert [i["id"] for i in available_power] == [saw["id"]]
    assert [i["id"] for i in on_loan] == [drill["id"]]


def test_unknown_item_returns_404(api: Api) -> None:  # ITEM-5
    response = api.client.get("/items/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NOT_FOUND"
