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


def _roi_set_payload(name: str = "Option 1") -> dict[str, object]:
    """Build a ROI set payload with one ROI per supported element."""
    return {
        "name": name,
        "rois": [
            {"name": name, "x": 10, "y": 20, "width": 100, "height": 30}
            for name in ["spin_button", "balance", "bet", "win"]
        ],
    }


def _create_roi_set(
    client: TestClient, provider_id: int, name: str = "Option 1"
) -> dict[str, object]:
    """Create a provider ROI set and return its response body."""
    response = client.post(
        f"/game-providers/{provider_id}/roi-sets",
        json=_roi_set_payload(name),
    )
    assert response.status_code == 201
    return response.json()


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
        "spin_wait_seconds": 12,
        "url": "https://example.com/starburst",
        "game_provider_id": provider_id,
        "roi_set_id": None,
        "roi_set": None,
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


def test_create_game_with_custom_spin_wait(client: TestClient) -> None:
    """The default spin wait can be overridden when creating a game."""
    provider_id = _create_provider(client)

    response = client.post(
        "/games",
        json=_game_payload(provider_id, spin_wait_seconds=5),
    )

    assert response.status_code == 201
    assert response.json()["spin_wait_seconds"] == 5


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


def test_create_game_with_existing_provider_roi_set(client: TestClient) -> None:
    """A game can reference an existing ROI set from its provider."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)

    response = client.post(
        "/games", json=_game_payload(provider_id, roi_set_id=roi_set["id"])
    )

    assert response.status_code == 201
    game = response.json()
    assert game["roi_set_id"] == roi_set["id"]
    assert game["roi_set"] == roi_set


def test_create_game_with_new_roi_set(client: TestClient) -> None:
    """A new game ROI set is also stored on the provider."""
    provider_id = _create_provider(client)
    payload = _roi_set_payload("Option 1")

    response = client.post(
        "/games", json=_game_payload(provider_id, roi_set=payload)
    )

    assert response.status_code == 201
    game = response.json()
    assert game["roi_set"]["name"] == "Option 1"
    assert game["roi_set_id"] == game["roi_set"]["id"]

    provider_sets = client.get(
        f"/game-providers/{provider_id}/roi-sets"
    ).json()
    assert [roi_set["id"] for roi_set in provider_sets] == [game["roi_set_id"]]


def test_create_game_new_roi_set_defaults_name(client: TestClient) -> None:
    """A game ROI set without a name is numbered for the provider."""
    provider_id = _create_provider(client)
    _create_roi_set(client, provider_id)

    response = client.post(
        "/games",
        json=_game_payload(provider_id, roi_set={"rois": []}),
    )

    assert response.status_code == 201
    assert response.json()["roi_set"]["name"] == "Option 2"


def test_create_game_rejects_roi_set_from_other_provider(
    client: TestClient,
) -> None:
    """A game cannot use a ROI set owned by another provider."""
    provider_id = _create_provider(client, "Steam")
    other_provider_id = _create_provider(client, "Epic")
    roi_set = _create_roi_set(client, other_provider_id)

    response = client.post(
        "/games", json=_game_payload(provider_id, roi_set_id=roi_set["id"])
    )

    assert response.status_code == 400


def test_create_game_rejects_two_roi_sources(client: TestClient) -> None:
    """A game payload cannot select and create a ROI set at once."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)

    response = client.post(
        "/games",
        json=_game_payload(
            provider_id,
            roi_set_id=roi_set["id"],
            roi_set=_roi_set_payload(),
        ),
    )

    assert response.status_code == 422


def test_update_game_roi_set_selection(client: TestClient) -> None:
    """A game can switch to a provider set, add a new set, or clear it."""
    provider_id = _create_provider(client)
    game = client.post("/games", json=_game_payload(provider_id)).json()
    first_set = _create_roi_set(client, provider_id)

    selected = client.patch(
        f"/games/{game['id']}", json={"roi_set_id": first_set["id"]}
    )

    assert selected.status_code == 200
    assert selected.json()["roi_set"] == first_set

    created = client.patch(
        f"/games/{game['id']}",
        json={"roi_set": _roi_set_payload("Option 2")},
    )

    assert created.status_code == 200
    assert created.json()["roi_set"]["name"] == "Option 2"
    assert len(
        client.get(f"/game-providers/{provider_id}/roi-sets").json()
    ) == 2

    cleared = client.patch(f"/games/{game['id']}", json={"roi_set_id": None})

    assert cleared.status_code == 200
    assert cleared.json()["roi_set_id"] is None
    assert cleared.json()["roi_set"] is None


def test_update_game_provider_clears_roi_set(client: TestClient) -> None:
    """Changing a game's provider detaches the old provider ROI set."""
    provider_id = _create_provider(client, "Steam")
    other_provider_id = _create_provider(client, "Epic")
    roi_set = _create_roi_set(client, provider_id)
    game = client.post(
        "/games", json=_game_payload(provider_id, roi_set_id=roi_set["id"])
    ).json()

    response = client.patch(
        f"/games/{game['id']}",
        json={"game_provider_id": other_provider_id},
    )

    assert response.status_code == 200
    assert response.json()["roi_set_id"] is None
    assert response.json()["roi_set"] is None


def test_delete_roi_set_detaches_game(client: TestClient) -> None:
    """Deleting a ROI set clears it from games that used it."""
    provider_id = _create_provider(client)
    roi_set = _create_roi_set(client, provider_id)
    game = client.post(
        "/games", json=_game_payload(provider_id, roi_set_id=roi_set["id"])
    ).json()

    assert client.delete(f"/roi-sets/{roi_set['id']}").status_code == 204

    fetched = client.get(f"/games/{game['id']}")

    assert fetched.status_code == 200
    assert fetched.json()["roi_set_id"] is None
    assert fetched.json()["roi_set"] is None
