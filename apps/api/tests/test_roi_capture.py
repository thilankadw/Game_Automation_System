"""Tests for the live ROI capture session endpoints."""

from fastapi.testclient import TestClient

URL = "/roi-capture/sessions"


def test_start_roi_capture_rejects_unknown_game(client: TestClient) -> None:
    """Starting a capture for a missing game returns 404 before launching."""
    response = client.post(URL, json={"game_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"


def test_start_roi_capture_validates_payload(client: TestClient) -> None:
    """A game ID is required and must be positive."""
    assert client.post(URL, json={}).status_code == 422
    assert client.post(URL, json={"game_id": 0}).status_code == 422


def test_session_endpoints_return_404_for_unknown_id(
    client: TestClient,
) -> None:
    """Reading or stopping an unknown session returns 404."""
    assert client.get(f"{URL}/does-not-exist").status_code == 404
    assert client.delete(f"{URL}/does-not-exist").status_code == 404


def test_list_sessions_is_empty_without_a_browser(
    client: TestClient,
) -> None:
    """No capture sessions exist until a game opens a Chrome window."""
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []
