from decimal import Decimal

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session


def create_expense(client, *, key="delete-me", group_id=1, user="bob", paid_by="alice"):
    response = client.post(
        f"/groups/{group_id}/expenses",
        headers={"X-User": user, "Idempotency-Key": key},
        json={
            "description": "Market dinner",
            "paid_by": paid_by,
            "amount": "100.00",
            "split": {"type": "exact", "shares": {"bob": "100.00", "carol": "0.00"}}
            if group_id == 1
            else {"type": "equal", "members": ["bob", "dan"]},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def stored_rows(engine):
    with engine.connect() as connection:
        expenses = (
            connection.execute(
                text(
                    "SELECT id, group_id, description, paid_by, amount, split_type, "
                    "idempotency_key, created_at, deleted FROM expenses ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
        shares = connection.execute(
            text(
                "SELECT expense_id, group_id, username, position, amount "
                "FROM expense_shares ORDER BY expense_id, position"
            )
        ).all()
    return [dict(expense) for expense in expenses], [tuple(share) for share in shares]


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


def test_payer_can_soft_delete_without_a_key_when_creator_and_split_members_differ(
    expense_client, expense_engine
):
    deleted = create_expense(expense_client)
    visible = create_expense(expense_client, key="keep-me")
    original_expenses, original_shares = stored_rows(expense_engine)
    assert deleted["paid_by"] == "alice"
    assert deleted["shares"] == {"bob": "100.00", "carol": "0.00"}

    response = expense_client.delete(
        f"/groups/1/expenses/{deleted['id']}", headers={"X-User": "alice"}
    )

    assert response.status_code == 204, response.text
    assert response.content == b""
    expenses, shares = stored_rows(expense_engine)
    assert expenses == [
        {**original_expenses[0], "deleted": True},
        original_expenses[1],
    ]
    assert shares == original_shares
    assert shares == [
        (deleted["id"], 1, "bob", 0, Decimal("100.00")),
        (deleted["id"], 1, "carol", 1, Decimal("0.00")),
        (visible["id"], 1, "bob", 0, Decimal("100.00")),
        (visible["id"], 1, "carol", 1, Decimal("0.00")),
    ]
    listing = expense_client.get("/groups/1/expenses", headers={"X-User": "bob"})
    assert listing.status_code == 200, listing.text
    assert listing.json() == [visible]

    repeated = expense_client.delete(
        f"/groups/1/expenses/{deleted['id']}", headers={"X-User": "alice"}
    )
    assert repeated.status_code == 204, repeated.text
    assert repeated.content == b""
    assert stored_rows(expense_engine) == (expenses, shares)


def test_deleted_expense_replay_retains_its_key_and_original_data_without_resurrection(
    expense_client, expense_engine
):
    created = create_expense(expense_client)
    original_expenses, original_shares = stored_rows(expense_engine)
    deleted = expense_client.delete(
        f"/groups/1/expenses/{created['id']}", headers={"X-User": "alice"}
    )
    assert deleted.status_code == 204, deleted.text

    replay = expense_client.post(
        "/groups/1/expenses",
        headers={"X-User": "carol", "Idempotency-Key": "delete-me"},
        json={
            "description": "Replacement",
            "paid_by": "carol",
            "amount": "25.00",
            "split": {"type": "equal", "members": ["carol"]},
        },
    )

    assert replay.status_code == 200, replay.text
    assert replay.json() == {**created, "deleted": True}
    assert stored_rows(expense_engine) == (
        [{**original_expenses[0], "deleted": True}],
        original_shares,
    )
    listing = expense_client.get("/groups/1/expenses", headers={"X-User": "alice"})
    assert listing.status_code == 200, listing.text
    assert listing.json() == []


@pytest.mark.parametrize("user", ["bob", "carol"])
@pytest.mark.parametrize("already_deleted", [False, True])
def test_nonpayer_cannot_delete_even_if_they_created_it_or_it_is_already_deleted(
    expense_client, expense_engine, user, already_deleted
):
    created = create_expense(expense_client)
    path = f"/groups/1/expenses/{created['id']}"
    if already_deleted:
        deleted = expense_client.delete(path, headers={"X-User": "alice"})
        assert deleted.status_code == 204, deleted.text
    original_rows = stored_rows(expense_engine)

    response = expense_client.delete(path, headers={"X-User": user})

    assert_error(response, 403, "expense_delete_forbidden")
    assert stored_rows(expense_engine) == original_rows


@pytest.mark.parametrize("headers", [{}, {"X-User": "nobody"}, {"X-User": ""}])
def test_delete_requires_a_known_request_user_without_modifying_the_expense(
    expense_client, expense_engine, headers
):
    created = create_expense(expense_client)
    original_rows = stored_rows(expense_engine)

    response = expense_client.delete(f"/groups/1/expenses/{created['id']}", headers=headers)

    assert_error(response, 401, "unauthenticated")
    assert stored_rows(expense_engine) == original_rows


@pytest.mark.parametrize("group_id", [2, 999])
def test_delete_hides_inaccessible_or_missing_groups_without_modifying_other_expenses(
    expense_client, expense_engine, group_id
):
    created = create_expense(expense_client)
    original_rows = stored_rows(expense_engine)

    response = expense_client.delete(
        f"/groups/{group_id}/expenses/{created['id']}", headers={"X-User": "alice"}
    )

    assert_error(response, 404, "group_not_found")
    assert stored_rows(expense_engine) == original_rows


@pytest.mark.parametrize("expense_from_other_group", [False, True])
def test_delete_hides_missing_and_other_group_expenses_from_a_member_of_both_groups(
    expense_client, expense_engine, expense_from_other_group
):
    other = create_expense(expense_client, group_id=2, paid_by="bob")
    original_rows = stored_rows(expense_engine)
    expense_id = other["id"] if expense_from_other_group else 999999

    response = expense_client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "bob"})

    assert_error(response, 404, "expense_not_found")
    assert stored_rows(expense_engine) == original_rows


@pytest.mark.parametrize("path", ["/groups/not-an-id/expenses/1", "/groups/1/expenses/not-an-id"])
def test_delete_rejects_noninteger_path_ids_without_modifying_expenses(
    expense_client, expense_engine, path
):
    create_expense(expense_client)
    original_rows = stored_rows(expense_engine)

    response = expense_client.delete(path, headers={"X-User": "alice"})

    assert response.status_code == 422, response.text
    assert stored_rows(expense_engine) == original_rows


def test_failed_delete_commit_preserves_the_expense_and_allows_a_later_retry(
    expense_client, expense_engine
):
    created = create_expense(expense_client)
    path = f"/groups/1/expenses/{created['id']}"
    original_expenses, original_shares = stored_rows(expense_engine)

    def fail_before_commit(session):
        session.flush()
        raise RuntimeError("forced delete commit failure")

    event.listen(Session, "before_commit", fail_before_commit)
    try:
        failed = expense_client.delete(path, headers={"X-User": "alice"})
    finally:
        event.remove(Session, "before_commit", fail_before_commit)

    assert_error(failed, 500, "internal_server_error")
    assert stored_rows(expense_engine) == (original_expenses, original_shares)
    listing = expense_client.get("/groups/1/expenses", headers={"X-User": "bob"})
    assert listing.status_code == 200, listing.text
    assert listing.json() == [created]

    retried = expense_client.delete(path, headers={"X-User": "alice"})
    assert retried.status_code == 204, retried.text
    assert retried.content == b""
    assert stored_rows(expense_engine) == (
        [{**original_expenses[0], "deleted": True}],
        original_shares,
    )
