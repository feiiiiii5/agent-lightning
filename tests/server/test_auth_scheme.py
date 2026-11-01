# Copyright (c) Microsoft. All rights reserved.

"""The HTTP authentication scheme is case-insensitive (RFC 7235 section 2.1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentlightning.server.app import create_app

ROLLOUTS_QUERY = {"state_in": "queuing"}


def _authorization_with_scheme(auth_headers: dict[str, str], scheme: str) -> dict[str, str]:
    _, _, token = auth_headers["Authorization"].partition(" ")
    return {"Authorization": f"{scheme} {token}"}


def test_lowercase_bearer_scheme_is_accepted(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = _authorization_with_scheme(auth_headers, "bearer")

    response = client.get("/api/rollouts", params=ROLLOUTS_QUERY, headers=headers)

    assert response.status_code == 200


def test_mixed_case_bearer_scheme_is_accepted(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = _authorization_with_scheme(auth_headers, "BeArEr")

    response = client.get("/api/rollouts", params=ROLLOUTS_QUERY, headers=headers)

    assert response.status_code == 200


def test_other_scheme_with_the_right_token_is_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = _authorization_with_scheme(auth_headers, "Basic")

    response = client.get("/api/rollouts", params=ROLLOUTS_QUERY, headers=headers)

    assert response.status_code == 401


def test_wrong_token_with_bearer_scheme_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/rollouts",
        params=ROLLOUTS_QUERY,
        headers={"Authorization": "Bearer not-the-key"},
    )

    assert response.status_code == 401


def test_extra_space_after_bearer_scheme_is_accepted(client: TestClient, auth_headers: dict[str, str]) -> None:
    _, _, token = auth_headers["Authorization"].partition(" ")
    headers = {"Authorization": f"Bearer  {token}"}

    response = client.get("/api/rollouts", params=ROLLOUTS_QUERY, headers=headers)

    assert response.status_code == 200


def test_key_that_begins_with_a_space_is_preserved() -> None:
    app = create_app(
        {
            "key": " secret",
            "default_proxy": {
                "model_name": "test-model",
                "train": {"temperature": 1},
                "val": {"temperature": 0},
            },
        }
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/rollouts",
            params=ROLLOUTS_QUERY,
            headers={"Authorization": "Bearer  secret"},
        )

    assert response.status_code == 200
