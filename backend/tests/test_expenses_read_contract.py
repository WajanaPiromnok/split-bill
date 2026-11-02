def test_expense_list_starts_empty_for_a_group_member(client):
    response = client.get("/groups/1/expenses", headers={"X-User": "alice"})

    assert response.status_code == 200
    assert response.json() == []
