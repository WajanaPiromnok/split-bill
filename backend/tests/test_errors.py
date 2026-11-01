from fastapi.testclient import TestClient

from splitbill import repository
from splitbill.app import create_app


def test_unexpected_failure_returns_safe_json_and_frontend_cors(
    database_url, seeded_engine, monkeypatch
):
    def database_failure(*args, **kwargs):
        raise RuntimeError("private database internals")

    monkeypatch.setattr(repository, "groups_for_user", database_failure)
    with TestClient(create_app(database_url), raise_server_exceptions=False) as client:
        response = client.get(
            "/groups", headers={"X-User": "alice", "Origin": "http://localhost:3000"}
        )
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_server_error", "message": "An unexpected error occurred"}
    }
    assert "private database internals" not in response.text
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
