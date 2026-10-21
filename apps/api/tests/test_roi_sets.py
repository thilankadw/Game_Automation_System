"""Tests for provider ROI set endpoints."""

from fastapi.testclient import TestClient

ROI_NAMES = ["spin_button", "balance", "bet", "win"]


def _rois() -> list[dict[str, object]]:
    """Build one ROI for each supported UI element."""
    return [
        {"name": name, "x": 10, "y": 20, "width": 100, "height": 30}
        for name in ROI_NAMES
    ]


def _create_provider(client: TestClient, name: str = "Steam") -> int:
    """Create a game provider and return its ID."""
    response = client.post("/game-providers", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_roi_set(
    client: TestClient, provider_id: int, **overrides: object
) -> dict[str, object]:
    """Create a ROI set with four ROIs and return the response body."""
    payload: dict[str, object] = {"name": "Option 1", "rois": _rois()}
    payload.update(overrides)
    response = client.post(
        f"/game-providers/{provider_id}/roi-sets", json=payload
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_get_roi_set(client: TestClient) -> None:
    """A created ROI set stores all four ROI types and can be fetched."""
    provider_id = _create_provider(client)

    roi_set = _create_roi_set(client, provider_id)

    assert roi_set["name"] == "Option 1"
    assert roi_set["game_provider_id"] == provider_id
    assert [roi["name"] for roi in roi_set["rois"]] == ROI_NAMES
    assert all(roi["x"] == 10 and roi["width"] == 100 for roi in roi_set["rois"])

    fetched = client.get(f"/roi-sets/{roi_set['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == roi_set


def test_roi_sets_default_to_option_names(client: TestClient) -> None:
    """ROI sets without a name are numbered per provider."""
    provider_id = _create_provider(client)

    first = _create_roi_set(client, provider_id, name=None)
    second = _create_roi_set(client, provider_id, name=None)

    assert first["name"] == "Option 1"
    assert second["name"] == "Option 2"

    listed = client.get(f"/game-providers/{provider_id}/roi-sets")

    assert listed.status_code == 200
    assert [roi_set["name"] for roi_set in listed.json()] == [
        "Option 1",
        "Option 2",
    ]


def test_roi_set_names_are_unique_per_provider(client: TestClient) -> None:
    """Two sets for the same provider cannot share a name."""
    provider_id = _create_provider(client)
    _create_roi_set(client, provider_id)

    response = client.post(
        f"/game-providers/{provider_id}/roi-sets",
        json={"name": "option 1", "rois": _rois()},
    )

    assert response.status_code == 409


def test_roi_set_validation(client: TestClient) -> None:
    """ROI names and coordinates must be valid and unique."""
    provider_id = _create_provider(client)
    url = f"/game-providers/{provider_id}/roi-sets"

    assert (
        client.post(
            url,
            json={"name": "Bad", "rois": [{"name": "jackpot", "x": 0, "y": 0, "width": 1, "height": 1}]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url,
            json={
                "name": "Duplicate",
                "rois": [
                    {"name": "bet", "x": 0, "y": 0, "width": 1, "height": 1},
                    {"name": "bet", "x": 1, "y": 1, "width": 1, "height": 1},
                ],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            url,
            json={
                "name": "Negative",
                "rois": [
                    {"name": "bet", "x": -1, "y": 0, "width": 1, "height": 1}
                ],
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            url,
            json={
                "name": "Zero",
                "rois": [
                    {"name": "bet", "x": 0, "y": 0, "width": 0, "height": 1}
                ],
            },
        ).status_code
        == 422
    )


def test_roi_set_missing_provider_or_set(client: TestClient) -> None:
    """Unknown providers and sets return 404."""
    assert client.post("/game-providers/9999/roi-sets", json={}).status_code == 404
    assert client.get("/game-providers/9999/roi-sets").status_code == 404
    assert client.get("/roi-sets/9999").status_code == 404


def test_update_roi_set_replaces_rois(client: TestClient) -> None:
    """Updating a ROI set can rename it and replace its ROI list."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)

    response = client.patch(
        f"/roi-sets/{roi_set['id']}",
        json={
            "name": "Option 3",
            "rois": [
                {"name": "bet", "x": 5, "y": 6, "width": 7, "height": 8},
                {"name": "win", "x": 9, "y": 10, "width": 11, "height": 12},
            ],
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Option 3"
    assert [roi["name"] for roi in updated["rois"]] == ["bet", "win"]
    assert updated["rois"][0] == {
        "id": updated["rois"][0]["id"],
        "name": "bet",
        "x": 5,
        "y": 6,
        "width": 7,
        "height": 8,
    }


def test_update_roi_set_rejects_duplicate_name(client: TestClient) -> None:
    """Renaming a set to another provider set's name returns 409."""
    provider_id = _create_provider(client)
    first = _create_roi_set(client, provider_id)
    _create_roi_set(client, provider_id, name="Option 2")

    response = client.patch(
        f"/roi-sets/{first['id']}", json={"name": "Option 2"}
    )

    assert response.status_code == 409


def test_delete_roi_set(client: TestClient) -> None:
    """A deleted ROI set can no longer be fetched."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)

    deleted = client.delete(f"/roi-sets/{roi_set['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/roi-sets/{roi_set['id']}").status_code == 404
    assert client.get(f"/game-providers/{provider_id}/roi-sets").json() == []


def test_delete_provider_removes_roi_sets(client: TestClient) -> None:
    """Deleting a provider also deletes the ROI sets it owns."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)

    assert client.delete(f"/game-providers/{provider_id}").status_code == 204

    assert client.get(f"/roi-sets/{roi_set['id']}").status_code == 404
    assert client.get(f"/game-providers/{provider_id}/roi-sets").status_code == 404
