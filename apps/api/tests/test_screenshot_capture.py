"""Tests for the automated screenshot capture session endpoints."""

import os
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.services import screenshot_capture
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


def test_stored_screenshots_require_a_known_game(client: TestClient) -> None:
    """Listing stored screenshots for a missing game returns 404."""
    response = client.get("/games/9999/screenshots")

    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"


def test_stored_screenshots_are_empty_without_a_folder(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A game with no capture folder has no stored screenshots."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Screenshot Provider")
    game = _create_game(client, provider_id, name="Screenshot Game")

    response = client.get(f"/games/{game['id']}/screenshots")

    assert response.status_code == 200
    assert response.json() == []


def test_stored_screenshots_list_sessions_newest_first(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored folders expose image URLs, counts, and capture dimensions."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Screenshot Provider")
    game = _create_game(client, provider_id, name="Screenshot Game")

    game_folder = tmp_path / "Screenshot Provider" / "Screenshot Game"
    older = game_folder / "older-session"
    newer = game_folder / "newer-session"
    for folder in (older, newer):
        folder.mkdir(parents=True)
        for index in (1, 2):
            image = Image.new("1", (1152, 648), color=1)
            image.save(folder / f"spin_{index:04d}.png")

    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    response = client.get(f"/games/{game['id']}/screenshots")

    assert response.status_code == 200
    sessions = response.json()
    assert [session["id"] for session in sessions] == [
        "newer-session",
        "older-session",
    ]
    assert sessions[0]["screenshot_count"] == 2
    assert sessions[0]["width"] == 1152
    assert sessions[0]["height"] == 648
    prefix = (
        "/screenshots/Screenshot%20Provider/Screenshot%20Game/newer-session"
    )
    assert sessions[0]["screenshots"] == [
        f"{prefix}/spin_0001.png",
        f"{prefix}/spin_0002.png",
    ]


def _write_session(folder: Path, count: int = 2) -> Path:
    """Create a stored session folder with black-and-white PNG frames."""
    folder.mkdir(parents=True, exist_ok=True)
    image = Image.new("1", (1152, 648), color=1)
    for index in range(1, count + 1):
        image.save(folder / f"spin_{index:04d}.png")
    return folder


def test_delete_stored_session_removes_only_that_session(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting one session keeps the game's other captures on disk."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")
    base = tmp_path / "Delete Provider" / "Delete Game"
    removed = _write_session(base / "session-to-remove")
    kept = _write_session(base / "session-to-keep", count=3)

    response = client.delete(
        f"/games/{game['id']}/screenshots/session-to-remove"
    )

    assert response.status_code == 204
    assert not removed.exists()
    assert (kept / "spin_0003.png").is_file()
    sessions = client.get(f"/games/{game['id']}/screenshots").json()
    assert [session["id"] for session in sessions] == ["session-to-keep"]


def test_delete_all_stored_sessions_removes_the_game_folder(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting all screenshots removes every session for the game."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")
    base = tmp_path / "Delete Provider" / "Delete Game"
    _write_session(base / "session-one")
    _write_session(base / "session-two")

    response = client.delete(f"/games/{game['id']}/screenshots")

    assert response.status_code == 204
    assert not base.exists()
    assert client.get(f"/games/{game['id']}/screenshots").json() == []


def test_delete_screenshots_handle_missing_folders(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing session is a 404, while deleting all is a no-op."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")

    missing = client.delete(
        f"/games/{game['id']}/screenshots/missing-session"
    )
    delete_all = client.delete(f"/games/{game['id']}/screenshots")

    assert missing.status_code == 404
    assert delete_all.status_code == 204


def test_delete_screenshots_requires_a_known_game(
    client: TestClient,
) -> None:
    """Deleting stored screenshots for a missing game returns 404."""
    assert client.delete("/games/9999/screenshots").status_code == 404
    assert (
        client.delete("/games/9999/screenshots/session").status_code == 404
    )


def test_delete_session_rejects_invalid_folder_names(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session names containing path syntax cannot remove other folders."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")
    base = tmp_path / "Delete Provider" / "Delete Game"
    _write_session(base / "safe-session")
    outside = tmp_path / "outside"
    _write_session(outside)

    response = client.delete(
        f"/games/{game['id']}/screenshots/{quote(str(outside), safe='')}"
    )

    assert response.status_code == 404
    assert (outside / "spin_0001.png").is_file()
    assert (base / "safe-session" / "spin_0001.png").is_file()


def test_delete_session_rejects_an_active_capture(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session cannot be deleted while its capture is still running."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")
    base = tmp_path / "Delete Provider" / "Delete Game"
    session = _write_session(base / "active-session")
    monkeypatch.setattr(
        screenshot_capture.manager,
        "active_session_ids",
        lambda: {"active-session"},
    )

    response = client.delete(
        f"/games/{game['id']}/screenshots/active-session"
    )

    assert response.status_code == 409
    assert session.is_dir()


def test_delete_all_rejects_an_active_capture(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bulk deletion is blocked while any capture is running for the game."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client, "Delete Provider")
    game = _create_game(client, provider_id, name="Delete Game")
    base = tmp_path / "Delete Provider" / "Delete Game"
    _write_session(base / "active-session")
    monkeypatch.setattr(
        screenshot_capture.manager,
        "active_game_ids",
        lambda: {game["id"]},
    )

    response = client.delete(f"/games/{game['id']}/screenshots")

    assert response.status_code == 409
    assert base.is_dir()


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
