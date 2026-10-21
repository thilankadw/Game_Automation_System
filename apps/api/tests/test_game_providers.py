"""Tests for the game provider endpoints."""

from fastapi.testclient import TestClient


def test_create_and_get_game_provider(client: TestClient) -> None:
    """A created provider can be fetched by ID."""
    created = client.post("/game-providers", json={"name": "Steam"})

    assert created.status_code == 201
    provider = created.json()
    assert provider == {"id": provider["id"], "name": "Steam"}

    fetched = client.get(f"/game-providers/{provider['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == provider


def test_create_rejects_empty_name(client: TestClient) -> None:
    """Provider names must not be empty."""
    response = client.post("/game-providers", json={"name": ""})

    assert response.status_code == 422


def test_get_missing_game_provider_returns_404(client: TestClient) -> None:
    """Fetching an unknown provider returns 404."""
    response = client.get("/game-providers/9999")

    assert response.status_code == 404


def test_list_filters_by_name_and_paginates(client: TestClient) -> None:
    """Listing supports case-insensitive name filtering and pagination."""
    for name in ["Steam", "Epic Games", "GOG", "Steam Keys"]:
        client.post("/game-providers", json={"name": name})

    response = client.get("/game-providers", params={"name": "steam", "limit": 1})

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 2
    assert page["skip"] == 0
    assert page["limit"] == 1
    assert [provider["name"] for provider in page["items"]] == ["Steam"]

    second_page = client.get(
        "/game-providers", params={"name": "steam", "skip": 1, "limit": 1}
    )

    assert [provider["name"] for provider in second_page.json()["items"]] == [
        "Steam Keys"
    ]


def test_update_game_provider(client: TestClient) -> None:
    """A provider name can be updated."""
    provider_id = client.post("/game-providers", json={"name": "Steam"}).json()["id"]

    response = client.patch(
        f"/game-providers/{provider_id}", json={"name": "Steam Store"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": provider_id, "name": "Steam Store"}


def test_delete_game_provider(client: TestClient) -> None:
    """A deleted provider can no longer be fetched."""
    provider_id = client.post("/game-providers", json={"name": "Steam"}).json()["id"]

    deleted = client.delete(f"/game-providers/{provider_id}")

    assert deleted.status_code == 204
    assert client.get(f"/game-providers/{provider_id}").status_code == 404
