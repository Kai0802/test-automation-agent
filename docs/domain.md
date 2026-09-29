# Tool Library: Domain Rules (v1)

A neighbourhood tool library. Members borrow tools (drills, ladders, tents),
return them, and pay late fees when they return them late.

This document is the source of truth for the behaviour of `apps/toollib`.
Every rule has an ID (e.g. `LOAN-3`) so tests and bug reports can refer to it.

## Conventions

- All money is stored and returned as **integer cents** (`100` = EUR 1.00).
- All timestamps are **UTC**, ISO-8601 with an offset (e.g. `2026-01-05T10:00:00Z`).
- "Now" always comes from the application clock, never from the system clock
  directly. In test mode the clock can be frozen and moved (see `TEST-*`).
- Errors use one shape:
  `{"error": {"code": "SOME_CODE", "message": "Human readable"}}`.
  Invalid request bodies or parameters return `422` with code `VALIDATION_ERROR`
  and a `details` list describing each invalid field.

## Entities

| Entity | Fields |
|---|---|
| Item | `id`, `name`, `category`, `status` (`available` \| `on_loan`), `created_at` |
| Member | `id`, `name`, `email` (unique), `fees_owed_cents`, `created_at` |
| Loan | `id`, `item_id`, `member_id`, `borrowed_at`, `due_at`, `returned_at` (nullable), `extended` (bool), `late_fee_cents` |

A loan is **active** while `returned_at` is null.

## Items

- **ITEM-1** A new item starts with status `available`.
- **ITEM-2** `name` is required, 1-100 characters after trimming whitespace.
- **ITEM-3** `category` is one of: `power_tools`, `hand_tools`, `garden`, `outdoor`, `ladders`.
- **ITEM-4** Items can be filtered by `status` and `category`.
- **ITEM-5** Unknown item id -> `404 ITEM_NOT_FOUND`.

## Members

- **MEM-1** `email` is unique (case-insensitive) -> `409 EMAIL_TAKEN`.
- **MEM-2** A new member owes `0` cents.
- **MEM-3** Unknown member id -> `404 MEMBER_NOT_FOUND`.

## Borrowing

- **LOAN-1** Only an `available` item can be borrowed -> otherwise `409 ITEM_NOT_AVAILABLE`.
- **LOAN-2** A member may have at most **3** active loans -> otherwise `409 LOAN_LIMIT_REACHED`.
- **LOAN-3** A member who owes **more than 1000 cents** (EUR 10.00) cannot borrow -> `409 MEMBER_BLOCKED`.
  Owing exactly 1000 cents is still allowed.
- **LOAN-4** `borrowed_at` = now. `due_at` = `borrowed_at` + **7 days**.
- **LOAN-5** Borrowing sets the item status to `on_loan`.
- **LOAN-6** When several rules fail, they are checked in this order and the first failure wins:
  member exists, item exists, `MEMBER_BLOCKED`, `LOAN_LIMIT_REACHED`, `ITEM_NOT_AVAILABLE`.

## Extending

- **EXT-1** A loan can be extended **once** -> second attempt `409 EXTENSION_NOT_ALLOWED`.
- **EXT-2** An overdue loan (now > `due_at`) cannot be extended -> `409 EXTENSION_NOT_ALLOWED`.
- **EXT-3** A returned loan cannot be extended -> `409 LOAN_ALREADY_RETURNED`.
- **EXT-4** Extending adds **7 days** to the current `due_at` (not to now).

## Returning

- **RET-1** Returning sets `returned_at` = now and the item status back to `available`.
- **RET-2** A loan can only be returned once -> `409 LOAN_ALREADY_RETURNED`.
- **RET-3** Late fee: **100 cents per started day** after `due_at`.
  Returned at or before `due_at` -> 0. One second late -> 100. Exactly 24h late -> 100.
  24h and one second late -> 200.
- **RET-4** The late fee is capped at **2000 cents** per loan.
- **RET-5** The late fee is stored on the loan and added to the member's `fees_owed_cents`.
- **RET-6** Unknown loan id -> `404 LOAN_NOT_FOUND`.

## Payments

- **PAY-1** A member pays with `amount_cents` > 0 -> otherwise `422`.
- **PAY-2** A payment cannot exceed `fees_owed_cents` -> `409 OVERPAYMENT`.
- **PAY-3** A payment reduces `fees_owed_cents` by `amount_cents`.

## Test-only endpoints

Enabled only when `TOOLLIB_TEST_MODE=true`. They are not part of the product
and return `404` when test mode is off.

- **TEST-1** `POST /__test__/reset` deletes all data and resets the clock to the real time.
- **TEST-2** `POST /__test__/clock` with `{"now": "<iso timestamp>"}` freezes the clock at that time.
- **TEST-3** `POST /__test__/clock/advance` with `{"seconds": N}` moves a frozen clock forward.
