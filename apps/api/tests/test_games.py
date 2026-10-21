"""Tests for the game endpoints."""

from fastapi.testclient import TestClient


def _create_provider(client: TestClient, name: str = "Steam") -> int:
    """Create a game provider and return its ID."""
    response = client.post("/game-providers", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _game_payload(provider_id: int, **overrides: object) -> dict[str, object]:
    """Build a valid game payload with optional field overrides."""
    payload: dict[str, object] = {
        "name": "Starburst",
        "url": "https://example.com/starburst",
        "game_provider_id": provider_id,
    }
    payload.update(overrides)
    return payload


def test_create_game_defaults_number_of_spins(client: TestClient) -> None:
    """A game created without a spin count defaults to 1000."""
    provider_id = _create_provider(client)

    response = client.post("/games", json=_game_payload(provider_id))

    assert response.status_code == 201
    game = response.json()
    assert game == {
        "id": game["id"],
        "name": "Starburst",
        "number_of_spins": 1000,
        "url": "https://example.com/starburst",
        "game_provider_id": provider_id,
    }


def test_create_game_with_custom_number_of_spins(client: TestClient) -> None:
    """The default spin count can be overridden when creating a game."""
    provider_id = _create_provider(client)

    response = client.post(
        "/games",
        json=_game_payload(provider_id, number_of_spins=250),
    )

    assert response.status_code == 201
    assert response.json()["number_of_spins"] == 250


def test_create_rejects_unknown_provider(client: TestClient) -> None:
    """A game must reference an existing provider."""
    response = client.post("/games", json=_game_payload(9999))

    assert response.status_code == 404


def test_create_rejects_invalid_payload(client: TestClient) -> None:
    """Game names, URLs, and spin counts must be valid."""
    provider_id = _create_provider(client)

    assert (
        client.post("/games", json=_game_payload(provider_id, name="")).status_code
        == 422
    )
    assert (
        client.post(
            "/games", json=_game_payload(provider_id, number_of_spins=-1)
        ).status_code
        == 422
    )
    assert (
        client.post("/games", json=_game_payload(provider_id, url="")).status_code
        == 422
    )


def test_get_game_by_id_and_name(client: TestClient) -> None:
    """A game can be fetched by ID or case-insensitive name."""
    provider_id = _create_provider(client)
    game = client.post("/games", json=_game_payload(provider_id)).json()

    by_id = client.get(f"/games/{game['id']}")
    by_name = client.get("/games/by-name/starburst")

    assert by_id.status_code == 200
    assert by_id.json() == game
    assert by_name.status_code == 200
    assert by_name.json() == game


def test_get_missing_game_returns_404(client: TestClient) -> None:
    """Fetching an unknown game or name returns 404."""
    assert client.get("/games/9999").status_code == 404
    assert client.get("/games/by-name/unknown").status_code == 404


def test_list_filters_by_name_and_paginates(client: TestClient) -> None:
    """Listing supports case-insensitive name filtering and pagination."""
    provider_id = _create_provider(client)
    for name in ["Starburst", "Star Fox", "Book of Dead", "Starburst XL"]:
        client.post("/games", json=_game_payload(provider_id, name=name))

    response = client.get("/games", params={"name": "star", "limit": 1})

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert page["skip"] == 0
    assert page["limit"] == 1
    assert [game["name"] for game in page["items"]] == ["Starburst"]

    second_page = client.get(
        "/games", params={"name": "star", "skip": 1, "limit": 1}
    )

    assert [game["name"] for game in second_page.json()["items"]] == ["Star Fox"]


def test_update_game_number_of_spins(client: TestClient) -> None:
    """The default number of spins can be edited."""
    provider_id = _create_provider(client)
    game = client.post("/games", json=_game_payload(provider_id)).json()

    response = client.patch(
        f"/games/{game['id']}", json={"number_of_spins": 2000}
    )

    assert response.status_code == 200
    assert response.json()["number_of_spins"] == 2000


def test_update_rejects_unknown_provider(client: TestClient) -> None:
    """Updating a game to reference an unknown provider returns 404."""
    provider_id = _create_provider(client)
    game = client.post("/games", json=_game_payload(provider_id)).json()

    response = client.patch(
        f"/games/{game['id']}", json={"game_provider_id": 9999}
    )

    assert response.status_code == 404


def test_delete_game(client: TestClient) -> None:
    """A deleted game can no longer be fetched."""
    provider_id = _create_provider(client)
    game = client.post("/games", json=_game_payload(provider_id)).json()

    deleted = client.delete(f"/games/{game['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/games/{game['id']}").status_code == 404
