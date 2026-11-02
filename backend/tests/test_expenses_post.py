from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Barrier, Lock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from splitbill.app import create_app


def expense_payload():
    return {
        "description": "Dinner at the night market",
        "paid_by": "alice",
        "amount": "100.00",
        "split": {"type": "equal", "members": ["alice", "bob", "carol"]},
    }


def post_expense(client, payload=None, *, group_id=1, user="alice", key="dinner-0001"):
    headers = {"X-User": user}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(
        f"/groups/{group_id}/expenses",
        headers=headers,
        json=expense_payload() if payload is None else payload,
    )


def assert_error(response, status=422, code=None):
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert isinstance(error["code"], str)
    assert isinstance(error["message"], str) and error["message"]
    if code is not None:
        assert error["code"] == code


def assert_stored_counts(engine, *, expenses, shares):
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM expenses")).scalar_one() == expenses
        assert (
            connection.execute(text("SELECT count(*) FROM expense_shares")).scalar_one() == shares
        )


def test_create_equal_expense_returns_complete_precise_representation(
    expense_client, expense_engine
):
    response = post_expense(expense_client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
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
    assert type(body["id"]) is int and body["id"] > 0
    assert body["group_id"] == 1
    assert body["description"] == "Dinner at the night market"
    assert body["paid_by"] == "alice"
    assert body["amount"] == "100.00"
    assert body["split_type"] == "equal"
    assert body["shares"] == {"alice": "33.34", "bob": "33.33", "carol": "33.33"}
    assert list(body["shares"]) == ["alice", "bob", "carol"]
    assert body["deleted"] is False
    created_at = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    assert created_at.utcoffset() == timedelta(0)
    with expense_engine.connect() as connection:
        stored = connection.execute(
            text(
                "SELECT username, amount, position FROM expense_shares "
                "WHERE expense_id = :id ORDER BY position"
            ),
            {"id": body["id"]},
        ).all()
        assert stored == [
            ("alice", Decimal("33.34"), 0),
            ("bob", Decimal("33.33"), 1),
            ("carol", Decimal("33.33"), 2),
        ]
    assert_stored_counts(expense_engine, expenses=1, shares=3)


@pytest.mark.parametrize(
    ("amount", "members", "expected"),
    [
        ("0.01", ["alice", "bob", "carol"], {"alice": "0.01", "bob": "0.00", "carol": "0.00"}),
        ("100", ["carol", "alice", "bob"], {"carol": "33.34", "alice": "33.33", "bob": "33.33"}),
        ("100.0", ["alice", "bob"], {"alice": "50.00", "bob": "50.00"}),
        ("9999999999.99", ["alice"], {"alice": "9999999999.99"}),
    ],
)
def test_equal_split_preserves_order_zero_shares_and_amount_range(
    expense_client, amount, members, expected
):
    payload = expense_payload()
    payload["amount"] = amount
    payload["split"]["members"] = members
    response = post_expense(expense_client, payload)

    assert response.status_code == 201, response.text
    assert response.json()["shares"] == expected
    assert list(response.json()["shares"]) == members
    assert sum((Decimal(share) for share in expected.values()), Decimal("0")) == Decimal(amount)


def test_create_exact_split_preserves_explicit_shares_and_zero(expense_client):
    payload = expense_payload()
    payload["split"] = {"type": "exact", "shares": {"carol": "0", "bob": "30", "alice": "70"}}
    response = post_expense(expense_client, payload)

    assert response.status_code == 201, response.text
    assert response.json()["split_type"] == "exact"
    assert response.json()["shares"] == {"carol": "0.00", "bob": "30.00", "alice": "70.00"}
    assert list(response.json()["shares"]) == ["carol", "bob", "alice"]


def test_member_can_record_another_payers_expense_without_payer_in_split(expense_client):
    payload = expense_payload()
    payload["split"]["members"] = ["bob", "carol"]
    response = post_expense(expense_client, payload, user="bob")

    assert response.status_code == 201, response.text
    assert response.json()["paid_by"] == "alice"
    assert response.json()["shares"] == {"bob": "50.00", "carol": "50.00"}


@pytest.mark.parametrize(
    "amount",
    [
        "0",
        "0.00",
        "-1.00",
        "10.005",
        "10.000",
        "NaN",
        "Infinity",
        "1e2",
        " 1.00",
        "1.00 ",
        "+1.00",
        "10000000000.00",
        "",
        100,
        100.0,
        True,
        None,
    ],
)
def test_invalid_amount_is_rejected_without_persisting_any_expense(
    expense_client, expense_engine, amount
):
    payload = expense_payload()
    payload["amount"] = amount
    assert_error(post_expense(expense_client, payload))
    assert_stored_counts(expense_engine, expenses=0, shares=0)


@pytest.mark.parametrize(
    "split",
    [
        {"type": "equal", "members": []},
        {"type": "equal", "members": ["alice", "alice"]},
        {"type": "equal", "members": ["alice", "dan"]},
        {"type": "exact", "shares": {}},
        {"type": "exact", "shares": {"alice": "99.99"}},
        {"type": "exact", "shares": {"alice": "-1.00", "bob": "101.00"}},
        {"type": "exact", "shares": {"alice": "100.000"}},
        {"type": "exact", "shares": {"alice": 100}},
        {"type": "exact", "shares": {"dan": "100.00"}},
        {"type": "percentage", "members": ["alice"]},
        {"type": "equal", "members": ["alice"], "shares": {"alice": "100.00"}},
    ],
)
def test_invalid_split_is_rejected_without_partial_rows(expense_client, expense_engine, split):
    payload = expense_payload()
    payload["split"] = split
    assert_error(post_expense(expense_client, payload))
    assert_stored_counts(expense_engine, expenses=0, shares=0)


@pytest.mark.parametrize("description", ["", "   ", "x" * 501])
def test_description_must_be_nonblank_and_bounded(expense_client, description):
    payload = expense_payload()
    payload["description"] = description
    assert_error(post_expense(expense_client, payload))


def test_unknown_top_level_fields_are_not_silently_accepted(expense_client):
    payload = expense_payload()
    payload["deleted"] = True
    assert_error(post_expense(expense_client, payload))


def test_payer_must_belong_to_the_group(expense_client, expense_engine):
    payload = expense_payload()
    payload["paid_by"] = "dan"
    assert_error(post_expense(expense_client, payload))
    assert_stored_counts(expense_engine, expenses=0, shares=0)


@pytest.mark.parametrize("key", [None, "", "   ", "x" * 201])
def test_idempotency_key_is_required_nonblank_and_bounded(expense_client, key):
    assert_error(post_expense(expense_client, key=key))


@pytest.mark.parametrize("headers", [{}, {"X-User": "nobody"}, {"X-User": ""}])
def test_only_known_request_users_can_create_expenses(expense_client, headers):
    response = expense_client.post(
        "/groups/1/expenses",
        headers={**headers, "Idempotency-Key": "dinner-0001"},
        json=expense_payload(),
    )
    assert_error(response, 401, "unauthenticated")


@pytest.mark.parametrize("group_id", [2, 999])
def test_nonmember_and_missing_groups_cannot_be_written(expense_client, group_id):
    assert_error(post_expense(expense_client, group_id=group_id), 404, "group_not_found")


@pytest.mark.parametrize("changed_amount", ["200.00", "10.005"])
def test_same_key_returns_original_expense_before_changed_business_rules(
    expense_client, expense_engine, changed_amount
):
    first = post_expense(expense_client)
    assert first.status_code == 201, first.text
    changed = deepcopy(expense_payload())
    changed.update(description="Changed", amount=changed_amount, paid_by="dan")
    changed["split"] = {"type": "equal", "members": ["dan"]}
    replay = post_expense(expense_client, changed, user="bob")

    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert_stored_counts(expense_engine, expenses=1, shares=3)


def test_identical_keys_are_independent_in_different_groups(expense_client, expense_engine):
    first = post_expense(expense_client, key="shared-key")
    lunch = expense_payload()
    lunch["paid_by"] = "bob"
    lunch["split"]["members"] = ["bob", "dan"]
    second = post_expense(expense_client, lunch, group_id=2, user="bob", key="shared-key")

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert second.json()["group_id"] == 2
    assert_stored_counts(expense_engine, expenses=2, shares=5)


def test_group_access_is_checked_before_returning_a_stored_key(expense_client):
    lunch = expense_payload()
    lunch["paid_by"] = "bob"
    lunch["split"]["members"] = ["bob", "dan"]
    first = post_expense(expense_client, lunch, group_id=2, user="bob")
    assert first.status_code == 201, first.text

    assert_error(post_expense(expense_client, lunch, group_id=2), 404, "group_not_found")


def test_soft_deleted_expense_keeps_its_idempotency_key(expense_client, expense_engine):
    first = post_expense(expense_client)
    assert first.status_code == 201, first.text
    with expense_engine.begin() as connection:
        connection.execute(
            text("UPDATE expenses SET deleted = true WHERE id = :id"), {"id": first.json()["id"]}
        )
    replay = post_expense(expense_client)

    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["deleted"] is True
    assert_stored_counts(expense_engine, expenses=1, shares=3)


def test_database_guards_key_uniqueness_for_the_group(expense_engine):
    constraints = inspect(expense_engine).get_unique_constraints("expenses")
    assert any(
        set(constraint["column_names"]) == {"group_id", "idempotency_key"}
        for constraint in constraints
    )


def test_simultaneous_same_key_requests_commit_one_complete_expense(
    expense_database_url, expense_engine, monkeypatch
):
    from splitbill import expense_repository

    original_lookup = expense_repository.get_expense_by_key
    barrier = Barrier(2, timeout=10)
    lock = Lock()
    participant_count = 0
    backend_pids = set()

    def synchronized_lookup(session, group_id, key):
        nonlocal participant_count
        expense = original_lookup(session, group_id, key)
        if key == "race-key" and expense is None:
            with lock:
                participant_count += 1
                participate = participant_count <= 2
                if participate:
                    backend_pids.add(session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            if participate:
                barrier.wait()
        return expense

    monkeypatch.setattr(expense_repository, "get_expense_by_key", synchronized_lookup)

    def send_request(_):
        with TestClient(create_app(expense_database_url)) as client:
            response = post_expense(client, key="race-key")
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send_request, range(2)))

    assert sorted(status for status, _ in responses) == [200, 201]
    assert responses[0][1] == responses[1][1]
    assert len(backend_pids) == 2
    assert_stored_counts(expense_engine, expenses=1, shares=3)


def test_share_failure_rolls_back_expense_and_key_then_allows_retry(
    expense_client, expense_engine, monkeypatch
):
    from splitbill import expense_repository

    original_add_shares = expense_repository.add_expense_shares

    def fail_after_shares(*args, **kwargs):
        original_add_shares(*args, **kwargs)
        raise RuntimeError("forced share write failure")

    with monkeypatch.context() as patch:
        patch.setattr(expense_repository, "add_expense_shares", fail_after_shares)
        failed = post_expense(expense_client)
    assert_error(failed, 500, "internal_server_error")
    assert_stored_counts(expense_engine, expenses=0, shares=0)

    retry = post_expense(expense_client)
    assert retry.status_code == 201, retry.text
    assert_stored_counts(expense_engine, expenses=1, shares=3)
