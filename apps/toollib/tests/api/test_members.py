import pytest

from conftest import Api


def test_create_member_owes_nothing(api: Api) -> None:  # MEM-2
    response = api.client.post("/members", json={"name": "Sam", "email": "Sam@Example.com"})

    assert response.status_code == 201
    assert response.json()["fees_owed_cents"] == 0
    assert response.json()["email"] == "sam@example.com"


def test_email_is_unique_case_insensitively(api: Api) -> None:  # MEM-1
    api.member(email="sam@example.com")

    response = api.client.post("/members", json={"name": "Other Sam", "email": "SAM@example.com"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


def test_invalid_email_is_rejected(api: Api) -> None:
    assert api.client.post("/members", json={"name": "Sam", "email": "not-an-email"}).status_code == 422


def test_unknown_member_returns_404(api: Api) -> None:  # MEM-3
    response = api.client.get("/members/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEMBER_NOT_FOUND"


def test_payment_reduces_fees(api: Api) -> None:  # PAY-3
    member = api.member()
    api.owe(member["id"], 500)

    response = api.client.post(f"/members/{member['id']}/payments", json={"amount_cents": 200})

    assert response.status_code == 200
    assert response.json()["fees_owed_cents"] == 300


def test_paying_the_exact_balance_clears_it(api: Api) -> None:  # PAY-2 boundary
    member = api.member()
    api.owe(member["id"], 500)

    response = api.client.post(f"/members/{member['id']}/payments", json={"amount_cents": 500})

    assert response.json()["fees_owed_cents"] == 0


def test_overpayment_is_rejected(api: Api) -> None:  # PAY-2
    member = api.member()
    api.owe(member["id"], 500)

    response = api.client.post(f"/members/{member['id']}/payments", json={"amount_cents": 501})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OVERPAYMENT"
    assert api.get_member(member["id"])["fees_owed_cents"] == 500


@pytest.mark.parametrize("amount", [0, -100])
def test_payment_must_be_positive(api: Api, amount: int) -> None:  # PAY-1
    member = api.member()

    response = api.client.post(f"/members/{member['id']}/payments", json={"amount_cents": amount})

    assert response.status_code == 422
