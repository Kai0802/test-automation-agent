from fastapi.testclient import TestClient

from conftest import Api
from toollib.config import Settings
from toollib.main import create_app


def test_reset_deletes_all_data(api: Api) -> None:  # TEST-1
    api.borrow(api.member()["id"], api.item()["id"])

    assert api.client.post("/__test__/reset").status_code == 204

    assert api.client.get("/items").json() == []
    assert api.client.get("/loans").json() == []


def test_clock_can_be_set_and_advanced(api: Api) -> None:  # TEST-2, TEST-3
    set_response = api.client.post("/__test__/clock", json={"now": "2026-03-01T12:00:00+02:00"})
    advance_response = api.client.post("/__test__/clock/advance", json={"seconds": 3600})

    assert set_response.json()["now"] == "2026-03-01T10:00:00Z"
    assert advance_response.json()["now"] == "2026-03-01T11:00:00Z"
    assert api.item()["created_at"] == "2026-03-01T11:00:00Z"


def test_clock_rejects_timestamps_without_timezone(api: Api) -> None:
    assert api.client.post("/__test__/clock", json={"now": "2026-03-01T12:00:00"}).status_code == 422


def test_test_endpoints_do_not_exist_outside_test_mode() -> None:
    app = create_app(Settings(database_url="sqlite://", test_mode=False))
    with TestClient(app) as client:
        assert client.post("/__test__/reset").status_code == 404
