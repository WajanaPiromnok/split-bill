import pytest


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        ("alice", [{"id": 1, "name": "Chiang Mai trip"}]),
        ("bob", [{"id": 1, "name": "Chiang Mai trip"}, {"id": 2, "name": "Office lunch"}]),
        ("carol", [{"id": 1, "name": "Chiang Mai trip"}]),
        ("dan", [{"id": 2, "name": "Office lunch"}]),
    ],
)
def test_only_requesting_users_groups_are_listed(client, user, expected):
    response = client.get("/groups", headers={"X-User": user})
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    ("user", "group_id", "name", "members"),
    [
        ("alice", 1, "Chiang Mai trip", ["alice", "bob", "carol"]),
        ("bob", 2, "Office lunch", ["bob", "dan"]),
    ],
)
def test_member_can_read_group_with_complete_members(client, user, group_id, name, members):
    response = client.get(f"/groups/{group_id}", headers={"X-User": user})
    assert response.status_code == 200
    assert response.json() == {"id": group_id, "name": name, "members": members}


@pytest.mark.parametrize("group_id", [2, 999])
def test_unauthorized_and_missing_groups_are_indistinguishable(client, group_id):
    response = client.get(f"/groups/{group_id}", headers={"X-User": "alice"})
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "group_not_found", "message": "Group not found"}}


@pytest.mark.parametrize("headers", [{}, {"X-User": ""}, {"X-User": "nobody"}])
@pytest.mark.parametrize("path", ["/groups", "/groups/1"])
def test_missing_empty_or_unknown_user_cannot_read_groups(client, headers, path):
    response = client.get(path, headers=headers)
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "unauthenticated", "message": "A valid X-User header is required"}
    }


def test_invalid_group_id_has_consistent_error_envelope(client):
    response = client.get("/groups/not-an-id", headers={"X-User": "alice"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"][0]["field"] == "path.group_id"
