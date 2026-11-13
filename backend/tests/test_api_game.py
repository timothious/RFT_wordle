"""API tests for human game play."""

from fastapi.testclient import TestClient

from backend.app.main import create_app


client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_play_game_without_leaking_answer() -> None:
    created = client.post("/games", json={"seed": 7})
    assert created.status_code == 201
    body = created.json()
    assert "answer" not in body
    assert body["status"] == "in_progress"
    assert body["remaining_guesses"] == 6
    game_id = body["game_id"]

    fetched = client.get(f"/games/{game_id}")
    assert fetched.status_code == 200
    assert "answer" not in fetched.json()

    bad = client.post(f"/games/{game_id}/guesses", json={"guess": "zzzzz"})
    assert bad.status_code == 400
    assert bad.json()["code"] == "not_in_dictionary"

    unchanged = client.get(f"/games/{game_id}").json()
    assert unchanged["board"] == []


def test_aeiou_is_an_allowed_guess() -> None:
    created = client.post("/games", json={"seed": 7})
    game_id = created.json()["game_id"]

    response = client.post(f"/games/{game_id}/guesses", json={"guess": "AEIOU"})

    assert response.status_code == 200
    assert response.json()["board"][0]["guess"] == "aeiou"


def test_not_found_game() -> None:
    response = client.get("/games/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
