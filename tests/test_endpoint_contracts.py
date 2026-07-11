import re

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.config import get_settings
from app.db.models import SteamAccount, User
from app.db.session import SessionLocal
from app.main import app, create_app


def _api_token_headers(monkeypatch) -> dict[str, str]:
    monkeypatch.setenv("API_TOKEN", "endpoint-contract-token")
    get_settings.cache_clear()
    return {"Authorization": "Bearer endpoint-contract-token"}


def _app_db_count(model) -> int:
    with SessionLocal() as session:
        return session.query(model).count()


def _api_route_methods(path: str) -> set[str]:
    for route in api_routes.router.routes:
        if getattr(route, "path", None) == path:
            return set(route.methods)
    raise AssertionError(f"API route missing: {path}")


def _health_endpoint():
    for route in app.routes:
        if getattr(route, "path", None) == "/health":
            return route.endpoint
    raise AssertionError("health route missing")


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def test_critical_endpoint_route_inventory_contract_is_stable():
    schema = app.openapi()

    assert schema["paths"]["/health"].keys() == {"get"}
    assert schema["paths"]["/api/matches"].keys() == {"get"}
    assert schema["paths"]["/api/coach/ai/result"].keys() == {"post"}
    assert schema["paths"]["/api/coach/ai/result/latest"].keys() == {"get"}
    assert _api_route_methods("/api/matches") == {"GET"}
    assert _api_route_methods("/api/coach/ai/result") == {"POST"}
    assert _api_route_methods("/api/coach/ai/result/latest") == {"GET"}


def test_public_health_serialization_contract_is_stable():
    assert _health_endpoint()() == {"status": "ok"}


def test_coach_domain_cards_require_owner_session_and_deny_cross_owner_access():
    with TestClient(app) as client:
        assert client.get("/api/coach/domains").status_code == 401
        register = client.get("/register")
        created = client.post(
            "/register",
            data={
                "csrf_token": _csrf_from(register),
                "display_name": "Owner",
                "email": "domain-owner@example.test",
                "password": "strong-password",
            },
            follow_redirects=False,
        )
        assert created.status_code == 303
        with SessionLocal() as session:
            owner = session.query(User).filter_by(email="domain-owner@example.test").one()
            session.add(SteamAccount(user_id=owner.id, steam_id="76561198000000017"))
            other = User(display_name="Other", email="domain-other@example.test", is_active=1)
            session.add(other)
            session.flush()
            session.add(SteamAccount(user_id=other.id, steam_id="76561198000000018"))
            session.commit()
            other_id = other.id
        own = client.get("/api/coach/domains")
        denied = client.get("/api/coach/domains", params={"owner_user_id": other_id})

    assert own.status_code == 200
    assert [card["domain"]["key"] for card in own.json()["cards"]] == [
        "impact_leak",
        "bad_fight_selection",
    ]
    assert denied.status_code == 403


def test_owner_api_read_serializes_empty_test_db_without_creating_user():
    with SessionLocal() as session:
        response = api_routes.list_matches(session)

    assert response == []
    assert _app_db_count(User) == 0


def test_ai_result_mutation_serializes_and_persists_to_test_db():
    with SessionLocal() as session:
        created = api_routes.save_ai_coach_result_endpoint(
            session,
            report_markdown="# Contract report\n\nUse only test data.",
            source_ref="endpoint-contract-test",
        )
        latest = api_routes.latest_ai_coach_result_endpoint(session)

    assert created["ok"] is True
    assert isinstance(created["id"], int)
    assert created["created_at"]
    assert latest["id"] == created["id"]
    assert latest["source_ref"] == "endpoint-contract-test"


def test_latest_ai_result_contract_returns_404_when_absent():
    with SessionLocal() as session:
        try:
            api_routes.latest_ai_coach_result_endpoint(session)
        except HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail == "No AI coach report saved yet"
        else:
            raise AssertionError("empty test DB should not have a latest AI result")


def test_live_api_latest_ai_result_translates_empty_state_to_404(monkeypatch):
    headers = _api_token_headers(monkeypatch)
    try:
        with TestClient(create_app()) as client:
            response = client.get("/api/coach/ai/result/latest", headers=headers)
    finally:
        get_settings.cache_clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "No AI coach report saved yet"


def test_live_api_ai_result_validation_error_is_400_without_persisting(monkeypatch):
    headers = _api_token_headers(monkeypatch)
    try:
        with TestClient(create_app()) as client:
            response = client.post(
                "/api/coach/ai/result",
                headers=headers,
                params={"report_markdown": "   ", "source_ref": "live-api-validation"},
            )
            latest = client.get("/api/coach/ai/result/latest", headers=headers)
    finally:
        get_settings.cache_clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "AI coach result is empty."
    assert latest.status_code == 404


def test_live_api_ai_result_roundtrip_exposes_payload_snapshot_metadata(monkeypatch):
    headers = _api_token_headers(monkeypatch)
    try:
        with TestClient(create_app()) as client:
            created = client.post(
                "/api/coach/ai/result",
                headers=headers,
                params={
                    "report_markdown": "# API validation\n\nUse only available test data.",
                    "source_ref": "live-api-validation",
                },
            )
            latest = client.get("/api/coach/ai/result/latest", headers=headers)
    finally:
        get_settings.cache_clear()

    assert created.status_code == 200
    assert created.json()["ok"] is True
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["id"] == created.json()["id"]
    assert payload["source_ref"] == "live-api-validation"
    assert payload["payload_hash"]
    assert payload["payload_matches_count"] == 0
    assert payload["metadata"]["payload_summary"]["matches_count"] == 0
    assert payload["metadata"]["ai_validation"]["valid"] is False
    assert payload["content_chars"] > 0
