"""Tests for the automated screenshot capture session endpoints."""

from fastapi.testclient import TestClient

from app.services.screenshot_capture import _safe_segment

URL = "/screenshot-capture/sessions"


def _create_provider(client: TestClient, name: str = "Steam") -> int:
    """Create a game provider and return its ID."""
    response = client.post("/game-providers", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_game(
    client: TestClient, provider_id: int, **overrides: object
) -> dict[str, object]:
    """Create a game for the provider and return its response body."""
    payload: dict[str, object] = {
        "name": "Starburst",
        "url": "https://example.com/starburst",
        "game_provider_id": provider_id,
    }
    payload.update(overrides)
    response = client.post("/games", json=payload)
    assert response.status_code == 201
    return response.json()


def _create_roi_set(
    client: TestClient,
    provider_id: int,
    names: tuple[str, ...] = ("spin_button", "balance", "bet", "win"),
) -> dict[str, object]:
    """Create a ROI set with the requested regions."""
    payload = {
        "name": "Option 1",
        "rois": [
            {"name": name, "x": 10, "y": 20, "width": 100, "height": 30}
            for name in names
        ],
    }
    response = client.post(
        f"/game-providers/{provider_id}/roi-sets", json=payload
    )
    assert response.status_code == 201
    return response.json()


def test_start_rejects_unknown_game(client: TestClient) -> None:
    """Starting a capture for a missing game returns 404."""
    response = client.post(URL, json={"game_id": 9999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"


def test_start_validates_payload(client: TestClient) -> None:
    """A game ID is required and must be positive."""
    assert client.post(URL, json={}).status_code == 422
    assert client.post(URL, json={"game_id": 0}).status_code == 422


def test_start_requires_an_assigned_roi_set(client: TestClient) -> None:
    """A game without a ROI set cannot start a capture."""
    provider_id = _create_provider(client)
    game = _create_game(client, provider_id)

    response = client.post(URL, json={"game_id": game["id"]})

    assert response.status_code == 422
    assert "Assign a ROI set" in response.json()["detail"]


def test_start_requires_the_spin_button_region(client: TestClient) -> None:
    """The ROI set must include the spin button region."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(
        client, provider_id, names=("balance", "bet", "win")
    )
    game = _create_game(client, provider_id, roi_set_id=roi_set["id"])

    response = client.post(URL, json={"game_id": game["id"]})

    assert response.status_code == 422
    assert "spin_button" in response.json()["detail"]


def test_session_endpoints_return_404_for_unknown_id(
    client: TestClient,
) -> None:
    """Reading or stopping an unknown session returns 404."""
    assert client.get(f"{URL}/does-not-exist").status_code == 404
    assert client.delete(f"{URL}/does-not-exist").status_code == 404


def test_list_sessions_is_empty_without_a_run(client: TestClient) -> None:
    """No screenshot sessions exist until a capture starts."""
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


def test_safe_segment_preserves_readable_names() -> None:
    """Spaces and ordinary characters are kept in folder names."""
    assert _safe_segment("Magic Stars", "game_1") == "Magic Stars"


def test_safe_segment_replaces_invalid_characters() -> None:
    """Windows path characters are replaced instead of rejected."""
    assert (
        _safe_segment('Wazdan: "Deluxe"', "provider_1")
        == "Wazdan_ _Deluxe_"
    )


def test_safe_segment_strips_trailing_dots_and_spaces() -> None:
    """Trailing dots and spaces, which Windows forbids, are removed."""
    assert _safe_segment("  Game.  ", "game_1") == "Game"


def test_safe_segment_prefixes_reserved_names() -> None:
    """Reserved Windows device names are made safe."""
    assert _safe_segment("CON", "game_1") == "_CON"


def test_safe_segment_truncates_and_uses_fallback() -> None:
    """Long names are truncated and unusable names fall back to IDs."""
    assert len(_safe_segment("x" * 200, "game_1")) == 60
    assert _safe_segment("   ", "game_1") == "game_1"
