from datetime import datetime, timedelta

import pytest
from sqlalchemy import text


def create_expense(
    client,
    *,
    key="dinner-0001",
    description="Dinner",
    group_id=1,
    user="alice",
    paid_by="alice",
    amount="100.00",
    split=None,
):
    response = client.post(
        f"/groups/{group_id}/expenses",
        headers={"X-User": user, "Idempotency-Key": key},
        json={
            "description": description,
            "paid_by": paid_by,
            "amount": amount,
            "split": split
            if split is not None
            else {"type": "equal", "members": ["alice", "bob", "carol"]},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_preserves_the_complete_created_expense_representation(expense_client):
    created = create_expense(expense_client)

    response = expense_client.get("/groups/1/expenses", headers={"X-User": "alice"})

    assert response.status_code == 200, response.text
    assert response.json() == [created]
    expense = response.json()[0]
    assert set(expense) == {
        "id",
        "group_id",
        "description",
        "paid_by",
        "amount",
        "split_type",
        "shares",
        "created_at",
        "deleted",
    }
    assert type(expense["id"]) is int
    assert expense["group_id"] == 1
    assert expense["description"] == "Dinner"
    assert expense["paid_by"] == "alice"
    assert expense["amount"] == "100.00"
    assert expense["split_type"] == "equal"
    assert expense["shares"] == {"alice": "33.34", "bob": "33.33", "carol": "33.33"}
    assert list(expense["shares"]) == ["alice", "bob", "carol"]
    assert expense["deleted"] is False
    created_at = datetime.fromisoformat(expense["created_at"].replace("Z", "+00:00"))
    assert created_at.utcoffset() == timedelta(0)


def test_list_preserves_exact_split_order_and_zero_amount_strings(expense_client):
    created = create_expense(
        expense_client,
        split={"type": "exact", "shares": {"carol": "0", "bob": "30", "alice": "70"}},
    )

    response = expense_client.get("/groups/1/expenses", headers={"X-User": "bob"})

    assert response.status_code == 200, response.text
    assert response.json() == [created]
    expense = response.json()[0]
    assert expense["split_type"] == "exact"
    assert expense["shares"] == {"carol": "0.00", "bob": "30.00", "alice": "70.00"}
    assert list(expense["shares"]) == ["carol", "bob", "alice"]


def test_list_returns_multiple_expenses_newest_first(expense_client):
    created = [
        create_expense(expense_client, key=f"expense-{number}", description=f"Meal {number}")
        for number in range(3)
    ]

    response = expense_client.get("/groups/1/expenses", headers={"X-User": "alice"})

    assert response.status_code == 200, response.text
    assert response.json() == list(reversed(created))


def test_list_orders_by_created_at_then_descending_id_for_ties(expense_client, expense_engine):
    first, second, third = [
        create_expense(expense_client, key=f"expense-{number}") for number in range(3)
    ]
    with expense_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE expenses SET created_at = CASE WHEN id = :newest_id "
                "THEN TIMESTAMPTZ '2026-11-02 12:00:00+00' "
                "ELSE TIMESTAMPTZ '2026-11-01 12:00:00+00' END"
            ),
            {"newest_id": first["id"]},
        )

    response = expense_client.get("/groups/1/expenses", headers={"X-User": "alice"})

    assert response.status_code == 200, response.text
    assert [expense["id"] for expense in response.json()] == [
        first["id"],
        third["id"],
        second["id"],
    ]


def test_list_only_contains_expenses_for_the_requested_group(expense_client):
    group_one = create_expense(expense_client, user="bob", key="shared-key")
    group_two = create_expense(
        expense_client,
        group_id=2,
        user="bob",
        paid_by="bob",
        key="shared-key",
        split={"type": "equal", "members": ["bob", "dan"]},
    )

    first_response = expense_client.get("/groups/1/expenses", headers={"X-User": "bob"})
    second_response = expense_client.get("/groups/2/expenses", headers={"X-User": "bob"})

    assert first_response.status_code == second_response.status_code == 200
    assert first_response.json() == [group_one]
    assert second_response.json() == [group_two]


def test_list_excludes_soft_deleted_expenses_without_removing_stored_rows(
    expense_client, expense_engine
):
    visible = create_expense(expense_client, key="visible")
    deleted = create_expense(expense_client, key="deleted")
    with expense_engine.begin() as connection:
        connection.execute(
            text("UPDATE expenses SET deleted = true WHERE id = :id"), {"id": deleted["id"]}
        )

    response = expense_client.get("/groups/1/expenses", headers={"X-User": "alice"})

    assert response.status_code == 200, response.text
    assert response.json() == [visible]
    with expense_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM expenses")).scalar_one() == 2
        assert connection.execute(text("SELECT count(*) FROM expense_shares")).scalar_one() == 6
        assert (
            connection.execute(
                text("SELECT deleted FROM expenses WHERE id = :id"), {"id": deleted["id"]}
            ).scalar_one()
            is True
        )


@pytest.mark.parametrize("headers", [{}, {"X-User": "nobody"}, {"X-User": ""}])
def test_list_requires_a_known_request_user(expense_client, headers):
    response = expense_client.get("/groups/1/expenses", headers=headers)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("group_id", [2, 999])
def test_list_hides_inaccessible_and_missing_groups(expense_client, group_id):
    response = expense_client.get(f"/groups/{group_id}/expenses", headers={"X-User": "alice"})

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "group_not_found"


def test_list_rejects_a_noninteger_group_id(expense_client):
    response = expense_client.get("/groups/not-an-id/expenses", headers={"X-User": "alice"})

    assert response.status_code == 422, response.text
