"""Tests for OCR extraction and stored spin readings."""

import time
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.services import ocr_extraction, screenshot_capture
from app.services.ocr_extraction import _parse_amount


def _create_provider(client: TestClient, name: str = "OCR Provider") -> int:
    """Create a game provider and return its ID."""
    response = client.post("/game-providers", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_roi_set(
    client: TestClient,
    provider_id: int,
    names: tuple[str, ...] = ("spin_button", "balance", "bet", "win"),
) -> dict[str, object]:
    """Create a ROI set with the requested regions."""
    payload = {
        "name": "OCR Layout",
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


def _create_game(
    client: TestClient,
    provider_id: int,
    roi_set_id: int | None,
    name: str = "OCR Game",
) -> dict[str, object]:
    """Create a game with an optional ROI set."""
    response = client.post(
        "/games",
        json={
            "name": name,
            "url": "https://example.com/ocr",
            "game_provider_id": provider_id,
            "roi_set_id": roi_set_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def _write_session(
    root: Path,
    provider_name: str,
    game_name: str,
    session_id: str,
    count: int = 2,
) -> Path:
    """Create a stored screenshot session with black-and-white frames."""
    folder = root / provider_name / game_name / session_id
    folder.mkdir(parents=True)
    image = Image.new("1", (200, 100), color=1)
    for index in range(1, count + 1):
        image.save(folder / f"spin_{index:04d}.png")
    return folder


def _wait_for_run(
    client: TestClient, game_id: int, run_id: str
) -> dict[str, object]:
    """Poll a background OCR run until it finishes."""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/games/{game_id}/ocr-runs/{run_id}")
        assert response.status_code == 200
        run = response.json()
        if run["status"] not in {"starting", "running"}:
            return run
        time.sleep(0.02)
    raise AssertionError("OCR run did not finish in time")


def _start_run(
    client: TestClient, game_id: int, session_id: str = "session-one"
) -> dict[str, object]:
    """Start an OCR run and wait for its completion."""
    response = client.post(
        f"/games/{game_id}/ocr-runs",
        json={"session_id": session_id},
    )
    assert response.status_code == 201
    run = _wait_for_run(client, game_id, response.json()["id"])
    assert run["status"] == "completed"
    return run


async def _fake_extract(
    path: Path, rois: dict[str, dict[str, int]]
) -> dict[str, str]:
    """Return deterministic OCR text without loading the real engine."""
    if path.name == "spin_0002.png":
        return {
            "balance": "2,500.00",
            "bet": "5.00",
            "win": "12.50",
        }
    return {
        "balance": "1,234.50",
        "bet": "5.00",
        "win": "Press Spin to Win",
    }


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("101,380.00", Decimal("101380.00")),
        ("1.234,56", Decimal("1234.56")),
        ("60.00", Decimal("60.00")),
        ("1,234", Decimal("1234.00")),
        ("1.234", Decimal("1234.00")),
        ("12", Decimal("12.00")),
        ("$ 5.50", Decimal("5.50")),
        ("Press Spin to Win", None),
        ("", None),
        ("-", None),
    ],
)
def test_parse_amount(text: str, expected: Decimal | None) -> None:
    """Common game display formats are parsed into two-decimal amounts."""
    assert _parse_amount(text) == expected


def test_ocr_run_stores_one_reading_per_frame(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed run stores parsed values and raw OCR text."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")

    run = _start_run(client, game["id"])

    assert run["total_spins"] == 2
    assert run["processed_spins"] == 2
    assert run["recognized_spins"] == 2
    assert run["roi_set_name"] == "OCR Layout"

    response = client.get(f"/games/{game['id']}/ocr-readings")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 2
    assert [item["spin_number"] for item in page["items"]] == [2, 1]

    latest = page["items"][0]
    assert latest["game_id"] == game["id"]
    assert latest["session_id"] == "session-one"
    assert latest["balance"] == 2500.0
    assert latest["bet"] == 5.0
    assert latest["win"] == 12.5
    assert latest["win_text"] == "12.50"
    assert latest["screenshot_path"].endswith(
        "/session-one/spin_0002.png"
    )

    first = page["items"][1]
    assert first["balance"] == 1234.5
    assert first["win"] is None
    assert first["win_text"] == "Press Spin to Win"


def test_ocr_rerun_replaces_session_readings(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reading the same session again does not duplicate stored rows."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")

    _start_run(client, game["id"])
    _start_run(client, game["id"])

    page = client.get(f"/games/{game['id']}/ocr-readings").json()
    assert page["total"] == 2


def test_ocr_readings_can_be_filtered_by_session(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The readings endpoint can restrict results to one stored session."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-two")

    _start_run(client, game["id"], "session-one")
    _start_run(client, game["id"], "session-two")

    page = client.get(
        f"/games/{game['id']}/ocr-readings",
        params={"session_id": "session-two"},
    ).json()
    assert page["total"] == 2
    assert {item["session_id"] for item in page["items"]} == {"session-two"}


def test_stored_sessions_include_ocr_reading_count(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Screenshot sessions report how many OCR readings they have."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")

    _start_run(client, game["id"])

    response = client.get(f"/games/{game['id']}/screenshots")
    assert response.status_code == 200
    sessions = response.json()
    assert sessions[0]["id"] == "session-one"
    assert sessions[0]["ocr_reading_count"] == 2


def test_delete_ocr_readings_for_one_session(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting one session's readings leaves the other session intact."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-two")

    _start_run(client, game["id"], "session-one")
    _start_run(client, game["id"], "session-two")

    response = client.delete(
        f"/games/{game['id']}/ocr-readings/session-one"
    )
    assert response.status_code == 204

    page = client.get(f"/games/{game['id']}/ocr-readings").json()
    assert page["total"] == 2
    assert {item["session_id"] for item in page["items"]} == {"session-two"}

    session_page = client.get(
        f"/games/{game['id']}/ocr-readings",
        params={"session_id": "session-one"},
    ).json()
    assert session_page["total"] == 0


def test_delete_all_ocr_readings(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting all readings clears every session for the game."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        ocr_extraction, "_extract_text_values_async", _fake_extract
    )
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-two")

    _start_run(client, game["id"], "session-one")
    _start_run(client, game["id"], "session-two")

    response = client.delete(f"/games/{game['id']}/ocr-readings")
    assert response.status_code == 204

    page = client.get(f"/games/{game['id']}/ocr-readings").json()
    assert page["total"] == 0
    assert page["items"] == []


def test_delete_ocr_readings_rejects_active_run(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readings cannot be deleted while an OCR run is still writing them."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    monkeypatch.setattr(
        ocr_extraction.manager,
        "active_run",
        lambda game_id, session_id=None: object(),
    )

    assert (
        client.delete(f"/games/{game['id']}/ocr-readings").status_code
        == 409
    )
    assert (
        client.delete(
            f"/games/{game['id']}/ocr-readings/session-one"
        ).status_code
        == 409
    )


def test_delete_ocr_readings_requires_a_known_game(
    client: TestClient,
) -> None:
    """Deleting readings for a missing game returns 404."""
    assert client.delete("/games/9999/ocr-readings").status_code == 404
    assert (
        client.delete("/games/9999/ocr-readings/session-one").status_code
        == 404
    )


def test_ocr_requires_balance_bet_and_win_regions(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ROI set without all three meter regions cannot start OCR."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(
        client, provider_id, names=("balance", "bet")
    )
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")

    response = client.post(
        f"/games/{game['id']}/ocr-runs",
        json={"session_id": "session-one"},
    )

    assert response.status_code == 422
    assert "win" in response.json()["detail"]


def test_ocr_requires_an_assigned_roi_set(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A game without a ROI set cannot start OCR."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client)
    game = _create_game(client, provider_id, None)
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")

    response = client.post(
        f"/games/{game['id']}/ocr-runs",
        json={"session_id": "session-one"},
    )

    assert response.status_code == 422
    assert "Assign a ROI set" in response.json()["detail"]


def test_ocr_rejects_missing_and_empty_sessions(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown sessions and folders without frames return clear errors."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    empty = tmp_path / "OCR Provider" / "OCR Game" / "empty-session"
    empty.mkdir(parents=True)

    missing = client.post(
        f"/games/{game['id']}/ocr-runs",
        json={"session_id": "missing-session"},
    )
    no_frames = client.post(
        f"/games/{game['id']}/ocr-runs",
        json={"session_id": "empty-session"},
    )

    assert missing.status_code == 404
    assert no_frames.status_code == 422
    assert "no frames" in no_frames.json()["detail"]


def test_ocr_rejects_an_active_capture(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session cannot be read while its capture is still running."""
    monkeypatch.setattr(screenshot_capture, "SCREENSHOT_DIR", tmp_path)
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = _create_game(client, provider_id, roi_set["id"])
    _write_session(tmp_path, "OCR Provider", "OCR Game", "session-one")
    monkeypatch.setattr(
        screenshot_capture.manager,
        "active_session_ids",
        lambda: {"session-one"},
    )

    response = client.post(
        f"/games/{game['id']}/ocr-runs",
        json={"session_id": "session-one"},
    )

    assert response.status_code == 409


def test_ocr_run_endpoints_require_a_known_game(
    client: TestClient,
) -> None:
    """Reading a missing game or run returns 404."""
    assert client.get("/games/9999/ocr-runs").status_code == 404
    assert client.get("/games/9999/ocr-runs/unknown").status_code == 404
    assert client.get("/games/9999/ocr-readings").status_code == 404
