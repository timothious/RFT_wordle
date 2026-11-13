"""API tests for suggestion endpoint (solver policy)."""

from fastapi.testclient import TestClient

from backend.app.main import create_app

client = TestClient(create_app())


def test_suggest_solver_and_optional_apply() -> None:
    created = client.post("/games", json={"seed": 3})
    assert created.status_code == 201
    game_id = created.json()["game_id"]

    suggested = client.post(
        f"/games/{game_id}/suggest",
        json={"policy": "solver", "apply": False},
    )
    assert suggested.status_code == 200
    body = suggested.json()
    assert body["raw_ok"] is True
    assert body["policy"] == "solver"
    assert body["guess"]
    assert body["applied"] is False

    applied = client.post(
        f"/games/{game_id}/suggest",
        json={"policy": "solver", "apply": True},
    )
    assert applied.status_code == 200
    applied_body = applied.json()
    assert applied_body["applied"] is True
    assert applied_body["board"] is not None
    assert len(applied_body["board"]["board"]) == 1


def test_suggest_base_disabled_without_lm() -> None:
    created = client.post("/games", json={"seed": 4})
    game_id = created.json()["game_id"]
    response = client.post(
        f"/games/{game_id}/suggest",
        json={"policy": "base", "apply": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["raw_ok"] is False
    assert "LM policies disabled" in (body["error"] or "")
