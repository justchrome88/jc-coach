from __future__ import annotations

import re
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_technical_sync_requires_authenticated_owner_and_csrf():
    with TestClient(app, follow_redirects=False) as client:
        assert client.get("/coach/technical-sync").status_code == 303
        assert client.post("/coach/technical-sync", data={"mode": "single"}).status_code == 403


def test_technical_sync_starts_one_owner_scoped_target_31_batch_and_renders_it():
    with TestClient(app, follow_redirects=False) as client:
        _register_owner(client)
        page = client.get("/coach/technical-sync")
        csrf = _csrf_from(page)
        first = client.post(
            "/coach/technical-sync",
            data={
                "csrf_token": csrf,
                "mode": "successful_target",
                "target_successful_new_matches": "31",
            },
        )
        second = client.post(
            "/coach/technical-sync",
            data={
                "csrf_token": csrf,
                "mode": "successful_target",
                "target_successful_new_matches": "31",
            },
        )

        assert first.status_code == second.status_code == 303
        assert first.headers["location"] == second.headers["location"]
        status = client.get(first.headers["location"])

    assert status.status_code == 200
    assert "Owner Sync Technical Console" in status.text
    assert "0 / 31" in status.text
    assert "owner_user_id" not in status.text
    assert "run_owner_coach_sync" not in status.text


def test_technical_sync_status_lookup_is_owner_scoped():
    with TestClient(app, follow_redirects=False) as client:
        _register_owner(client)
        response = client.get("/coach/technical-sync/status?batch_id=not-owned")

    assert response.status_code == 404


def _register_owner(client: TestClient) -> None:
    page = client.get("/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Technical Owner",
            "email": f"test-{uuid4().hex}@example.test",
            "password": "test-password",
        },
    )
    assert response.status_code == 303


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)
