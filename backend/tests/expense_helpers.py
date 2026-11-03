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
    status=201,
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
    assert response.status_code == status, response.text
    return response.json()
