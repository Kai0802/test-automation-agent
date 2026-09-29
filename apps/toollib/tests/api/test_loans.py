from conftest import Api


def error_code(response) -> str:  # type: ignore[no-untyped-def]
    return response.json()["error"]["code"]


# ---- borrowing -----------------------------------------------------------


def test_borrow_sets_due_date_and_marks_item_on_loan(api: Api) -> None:  # LOAN-4, LOAN-5
    member, item = api.member(), api.item()

    loan = api.borrow(member["id"], item["id"])

    assert loan["borrowed_at"] == "2026-01-05T10:00:00Z"
    assert loan["due_at"] == "2026-01-12T10:00:00Z"
    assert loan["returned_at"] is None
    assert loan["extended"] is False
    assert api.client.get(f"/items/{item['id']}").json()["status"] == "on_loan"


def test_cannot_borrow_an_item_on_loan(api: Api) -> None:  # LOAN-1
    item = api.item()
    api.borrow(api.member()["id"], item["id"])

    response = api.client.post("/loans", json={"member_id": api.member()["id"], "item_id": item["id"]})

    assert response.status_code == 409
    assert error_code(response) == "ITEM_NOT_AVAILABLE"


def test_loan_limit_is_three_active_loans(api: Api) -> None:  # LOAN-2
    member = api.member()
    for _ in range(3):
        api.borrow(member["id"], api.item()["id"])

    response = api.client.post("/loans", json={"member_id": member["id"], "item_id": api.item()["id"]})

    assert response.status_code == 409
    assert error_code(response) == "LOAN_LIMIT_REACHED"


def test_returned_loans_do_not_count_towards_the_limit(api: Api) -> None:  # LOAN-2
    member = api.member()
    loans = [api.borrow(member["id"], api.item()["id"]) for _ in range(3)]
    api.return_loan(loans[0]["id"])

    api.borrow(member["id"], api.item()["id"])


def test_owing_exactly_ten_euros_can_still_borrow(api: Api) -> None:  # LOAN-3 boundary
    member = api.member()
    api.owe(member["id"], 1000)

    api.borrow(member["id"], api.item()["id"])


def test_owing_more_than_ten_euros_blocks_borrowing(api: Api) -> None:  # LOAN-3
    member = api.member()
    api.owe(member["id"], 1100)

    response = api.client.post("/loans", json={"member_id": member["id"], "item_id": api.item()["id"]})

    assert response.status_code == 409
    assert error_code(response) == "MEMBER_BLOCKED"


def test_blocked_is_reported_before_unavailable(api: Api) -> None:  # LOAN-6
    member = api.member()
    api.owe(member["id"], 1100)
    item = api.item()
    api.borrow(api.member()["id"], item["id"])

    response = api.client.post("/loans", json={"member_id": member["id"], "item_id": item["id"]})

    assert error_code(response) == "MEMBER_BLOCKED"


def test_borrow_with_unknown_member_or_item(api: Api) -> None:  # LOAN-6
    item, member = api.item(), api.member()

    no_member = api.client.post("/loans", json={"member_id": 999, "item_id": item["id"]})
    no_item = api.client.post("/loans", json={"member_id": member["id"], "item_id": 999})

    assert (no_member.status_code, error_code(no_member)) == (404, "MEMBER_NOT_FOUND")
    assert (no_item.status_code, error_code(no_item)) == (404, "ITEM_NOT_FOUND")


# ---- extending -----------------------------------------------------------


def test_extend_adds_seven_days_to_the_due_date(api: Api) -> None:  # EXT-4
    loan = api.borrow(api.member()["id"], api.item()["id"])
    api.advance(days=3)

    response = api.client.post(f"/loans/{loan['id']}/extend")

    assert response.status_code == 200
    assert response.json()["due_at"] == "2026-01-19T10:00:00Z"  # due_at + 7, not now + 7
    assert response.json()["extended"] is True


def test_extend_only_once(api: Api) -> None:  # EXT-1
    loan = api.borrow(api.member()["id"], api.item()["id"])
    api.client.post(f"/loans/{loan['id']}/extend")

    response = api.client.post(f"/loans/{loan['id']}/extend")

    assert response.status_code == 409
    assert error_code(response) == "EXTENSION_NOT_ALLOWED"


def test_cannot_extend_overdue_loan(api: Api) -> None:  # EXT-2
    loan = api.borrow(api.member()["id"], api.item()["id"])
    api.advance(days=7, seconds=1)

    response = api.client.post(f"/loans/{loan['id']}/extend")

    assert error_code(response) == "EXTENSION_NOT_ALLOWED"


def test_cannot_extend_returned_loan(api: Api) -> None:  # EXT-3
    loan = api.borrow(api.member()["id"], api.item()["id"])
    api.return_loan(loan["id"])

    response = api.client.post(f"/loans/{loan['id']}/extend")

    assert error_code(response) == "LOAN_ALREADY_RETURNED"


# ---- returning -----------------------------------------------------------


def test_on_time_return_has_no_fee_and_frees_the_item(api: Api) -> None:  # RET-1
    member, item = api.member(), api.item()
    loan = api.borrow(member["id"], item["id"])
    api.advance(days=7)

    returned = api.return_loan(loan["id"])

    assert returned["returned_at"] == "2026-01-12T10:00:00Z"
    assert returned["late_fee_cents"] == 0
    assert api.client.get(f"/items/{item['id']}").json()["status"] == "available"


def test_late_return_charges_the_member(api: Api) -> None:  # RET-3, RET-5
    member = api.member()
    loan = api.borrow(member["id"], api.item()["id"])
    api.advance(days=9, hours=1)  # 2 days and 1 hour late -> 3 started days

    returned = api.return_loan(loan["id"])

    assert returned["late_fee_cents"] == 300
    assert api.get_member(member["id"])["fees_owed_cents"] == 300


def test_late_fee_is_capped_per_loan(api: Api) -> None:  # RET-4
    member = api.member()
    loan = api.borrow(member["id"], api.item()["id"])
    api.advance(days=60)

    assert api.return_loan(loan["id"])["late_fee_cents"] == 2000


def test_fees_from_several_loans_add_up(api: Api) -> None:  # RET-5
    member = api.member()
    first = api.borrow(member["id"], api.item()["id"])
    second = api.borrow(member["id"], api.item()["id"])
    api.advance(days=8)

    api.return_loan(first["id"])
    api.return_loan(second["id"])

    assert api.get_member(member["id"])["fees_owed_cents"] == 200


def test_return_twice_is_rejected(api: Api) -> None:  # RET-2
    loan = api.borrow(api.member()["id"], api.item()["id"])
    api.return_loan(loan["id"])

    response = api.client.post(f"/loans/{loan['id']}/return")

    assert response.status_code == 409
    assert error_code(response) == "LOAN_ALREADY_RETURNED"


def test_unknown_loan_returns_404(api: Api) -> None:  # RET-6
    response = api.client.post("/loans/999/return")

    assert response.status_code == 404
    assert error_code(response) == "LOAN_NOT_FOUND"


# ---- listing -------------------------------------------------------------


def test_list_loans_by_member_and_active(api: Api) -> None:
    alex, sam = api.member(), api.member()
    returned = api.borrow(alex["id"], api.item()["id"])
    active = api.borrow(alex["id"], api.item()["id"])
    api.borrow(sam["id"], api.item()["id"])
    api.return_loan(returned["id"])

    def ids(**params: object) -> list[int]:
        return [loan["id"] for loan in api.client.get("/loans", params=params).json()]

    assert ids(member_id=alex["id"]) == [returned["id"], active["id"]]
    assert ids(member_id=alex["id"], active=True) == [active["id"]]
    assert ids(member_id=alex["id"], active=False) == [returned["id"]]
