from decimal import Decimal

import pytest
from expense_helpers import create_expense
from sqlalchemy import text


def get_balances(client, *, group_id=1, user="alice"):
    response = client.get(f"/groups/{group_id}/balances", headers={"X-User": user})
    assert response.status_code == 200, response.text
    return response.json()


def test_empty_group_returns_all_members_in_alphabetical_order(expense_client, expense_engine):
    with expense_engine.begin() as connection:
        connection.execute(text("INSERT INTO groups (id, name) VALUES (3, 'Unsorted members')"))
        connection.execute(
            text(
                "INSERT INTO group_members (group_id, username) "
                "VALUES (3, 'carol'), (3, 'alice'), (3, 'bob')"
            )
        )

    balances = get_balances(expense_client, group_id=3, user="bob")

    assert balances == {"alice": "0.00", "bob": "0.00", "carol": "0.00"}
    assert list(balances) == ["alice", "bob", "carol"]


@pytest.mark.parametrize(
    ("amount", "shares", "expected"),
    [
        (
            "100.00",
            {"alice": "33.34", "bob": "33.33", "carol": "33.33"},
            {"alice": "66.66", "bob": "-33.33", "carol": "-33.33"},
        ),
        (
            "1000.00",
            {"alice": "333.34", "bob": "333.33", "carol": "333.33"},
            {"alice": "666.66", "bob": "-333.33", "carol": "-333.33"},
        ),
    ],
)
def test_equal_expense_credits_the_payer_minus_the_payers_rounded_share(
    expense_client, amount, shares, expected
):
    created = create_expense(expense_client, amount=amount)

    balances = get_balances(expense_client)

    assert created["shares"] == shares
    assert balances == expected
    assert list(balances) == ["alice", "bob", "carol"]
    assert sum((Decimal(value) for value in balances.values()), Decimal("0.00")) == Decimal("0.00")


def test_balances_use_the_stored_remainder_order_and_include_zero_shares(expense_client):
    created = create_expense(
        expense_client,
        amount="0.02",
        split={"type": "equal", "members": ["carol", "alice", "bob"]},
    )

    balances = get_balances(expense_client)

    assert created["shares"] == {"carol": "0.01", "alice": "0.01", "bob": "0.00"}
    assert balances == {"alice": "0.01", "bob": "0.00", "carol": "-0.01"}
    assert list(balances) == ["alice", "bob", "carol"]


def test_exact_split_includes_explicit_zero_and_omitted_members_without_negative_zero(
    expense_client,
):
    create_expense(
        expense_client,
        split={"type": "exact", "shares": {"alice": "100", "bob": "0"}},
    )

    balances = get_balances(expense_client, user="carol")

    assert balances == {"alice": "0.00", "bob": "0.00", "carol": "0.00"}


@pytest.mark.parametrize(
    "split",
    [
        {"type": "equal", "members": ["bob", "carol"]},
        {"type": "exact", "shares": {"bob": "45.00", "carol": "45.00"}},
    ],
)
def test_payer_receives_full_credit_when_another_member_records_a_split_excluding_them(
    expense_client, split
):
    create_expense(expense_client, user="bob", amount="90.00", split=split)

    balances = get_balances(expense_client, user="carol")

    assert balances == {"alice": "90.00", "bob": "-45.00", "carol": "-45.00"}


def test_exact_split_keeps_a_one_satang_debt_and_untouched_member(expense_client):
    create_expense(
        expense_client,
        amount="0.01",
        split={"type": "exact", "shares": {"bob": "0.01"}},
    )

    balances = get_balances(expense_client)

    assert balances == {"alice": "0.01", "bob": "-0.01", "carol": "0.00"}


def test_replaying_an_idempotency_key_does_not_count_the_expense_twice(expense_client):
    original = create_expense(expense_client)
    replay = create_expense(
        expense_client,
        user="bob",
        paid_by="carol",
        amount="900.00",
        status=200,
    )

    balances = get_balances(expense_client)

    assert replay["id"] == original["id"]
    assert balances == {"alice": "66.66", "bob": "-33.33", "carol": "-33.33"}


def test_multiple_payers_and_different_split_sizes_accumulate_paid_minus_owed(expense_client):
    create_expense(expense_client, key="alice-paid", amount="120.00")
    create_expense(
        expense_client,
        key="bob-paid",
        paid_by="bob",
        amount="90.00",
        split={"type": "exact", "shares": {"alice": "10", "bob": "20", "carol": "60"}},
    )
    create_expense(
        expense_client,
        key="carol-paid",
        paid_by="carol",
        amount="10.01",
        split={"type": "exact", "shares": {"alice": "0.01", "bob": "10"}},
    )

    balances = get_balances(expense_client, user="bob")

    # Paid: 120, 90, 10.01. Owed: 50.01, 70, 100.
    assert balances == {"alice": "69.99", "bob": "20.00", "carol": "-89.99"}
    assert sum((Decimal(value) for value in balances.values()), Decimal("0.00")) == Decimal("0.00")


def test_shared_member_balances_and_identical_keys_stay_within_their_group(expense_client):
    create_expense(expense_client, user="bob", key="shared-key")
    create_expense(
        expense_client,
        key="shared-key",
        group_id=2,
        user="bob",
        paid_by="bob",
        amount="90.00",
        split={"type": "equal", "members": ["bob", "dan"]},
    )

    first_group = get_balances(expense_client, user="bob")
    second_group = get_balances(expense_client, group_id=2, user="bob")

    assert first_group == {"alice": "66.66", "bob": "-33.33", "carol": "-33.33"}
    assert second_group == {"bob": "45.00", "dan": "-45.00"}


def test_successful_deletion_removes_both_paid_and_owed_until_every_balance_is_zero(
    expense_client,
):
    first = create_expense(expense_client)
    second = create_expense(
        expense_client,
        key="bob-paid",
        paid_by="bob",
        amount="60.00",
        split={"type": "exact", "shares": {"alice": "30", "carol": "30"}},
    )
    assert get_balances(expense_client) == {
        "alice": "36.66",
        "bob": "26.67",
        "carol": "-63.33",
    }

    response = expense_client.delete(
        f"/groups/1/expenses/{second['id']}", headers={"X-User": "bob"}
    )

    assert response.status_code == 204, response.text
    assert get_balances(expense_client) == {
        "alice": "66.66",
        "bob": "-33.33",
        "carol": "-33.33",
    }

    response = expense_client.delete(
        f"/groups/1/expenses/{first['id']}", headers={"X-User": "alice"}
    )

    assert response.status_code == 204, response.text
    assert get_balances(expense_client) == {"alice": "0.00", "bob": "0.00", "carol": "0.00"}


def test_denied_nonpayer_deletion_does_not_change_balances(expense_client):
    created = create_expense(expense_client)
    assert get_balances(expense_client) == {
        "alice": "66.66",
        "bob": "-33.33",
        "carol": "-33.33",
    }

    response = expense_client.delete(
        f"/groups/1/expenses/{created['id']}", headers={"X-User": "bob"}
    )

    assert response.status_code == 403, response.text
    assert get_balances(expense_client) == {
        "alice": "66.66",
        "bob": "-33.33",
        "carol": "-33.33",
    }


def test_aggregate_balances_can_exceed_the_maximum_single_expense_amount(expense_client):
    for key in ("maximum-one", "maximum-two", "maximum-three"):
        create_expense(
            expense_client,
            key=key,
            amount="9999999999.99",
            split={"type": "exact", "shares": {"bob": "9999999999.99"}},
        )

    balances = get_balances(expense_client)

    assert balances == {
        "alice": "29999999999.97",
        "bob": "-29999999999.97",
        "carol": "0.00",
    }


@pytest.mark.parametrize("headers", [{}, {"X-User": "nobody"}, {"X-User": ""}])
def test_balances_require_a_known_request_user(expense_client, headers):
    response = expense_client.get("/groups/1/balances", headers=headers)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("group_id", [2, 999])
def test_balances_hide_inaccessible_and_missing_groups(expense_client, group_id):
    response = expense_client.get(f"/groups/{group_id}/balances", headers={"X-User": "alice"})

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "group_not_found"


def test_balances_reject_a_noninteger_group_id(expense_client):
    response = expense_client.get("/groups/not-an-id/balances", headers={"X-User": "alice"})

    assert response.status_code == 422, response.text
