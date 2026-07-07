from fastapi import HTTPException

from app.api import routes as api_routes
from app.db.models import User
from app.db.session import SessionLocal
from app.main import app


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
