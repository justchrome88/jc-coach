import re

from fastapi.testclient import TestClient

from app.db.models import CoachReport, DemoParseArtifact, ImportJob, Match, SteamAccount, User
from app.db.session import SessionLocal
from app.main import app, create_app
from app.services.auth import (
    active_credentialed_test_smoke_users,
    current_user_from_session,
    hash_password,
    owner_user,
    register_user,
)
from app.services.metrics.snapshots import create_metric_snapshot
from app.services.ownership import (
    get_owned_coach_report,
    get_owned_import_job,
    get_owned_match,
    get_owned_metric_snapshot,
    get_owned_parse_artifact,
)


def _csrf_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _register_via_web(client: TestClient, email: str = "owner@example.test"):
    page = client.get("/register")
    return client.post(
        "/register",
        data={
            "csrf_token": _csrf_from(page),
            "display_name": "Owner",
            "email": email,
            "password": "strong-password",
        },
        follow_redirects=False,
    )


def _app_db_count(model) -> int:
    session = SessionLocal()
    try:
        return session.query(model).count()
    finally:
        session.close()


def _app_db_one(model):
    session = SessionLocal()
    try:
        value = session.query(model).one()
        session.expunge(value)
        return value
    finally:
        session.close()


def test_first_user_registration_works(db):
    user = register_user(db, "owner@example.test", "strong-password", display_name="Owner")

    assert user.id is not None
    assert owner_user(db).id == user.id


def test_legacy_steam_only_user_does_not_become_owner(db):
    legacy_user = User(display_name="Steam Legacy", is_active=1)
    db.add(legacy_user)
    db.commit()

    user = register_user(db, "owner@example.test", "strong-password", display_name="Owner")

    assert owner_user(db).id == user.id
    assert user.id != legacy_user.id


def test_second_user_registration_blocked_by_default(db):
    register_user(db, "owner@example.test", "strong-password", display_name="Owner")

    try:
        register_user(db, "second@example.test", "strong-password", display_name="Second")
    except ValueError as exc:
        assert "Регистрация закрыта" in str(exc)
    else:
        raise AssertionError("second user registration should be blocked")


def test_blocked_second_user_is_not_created_in_db(db):
    register_user(db, "owner@example.test", "strong-password", display_name="Owner")

    try:
        register_user(db, "second@example.test", "strong-password", display_name="Second")
    except ValueError:
        pass

    assert db.query(User).count() == 1


def test_web_first_registration_works_and_second_registration_blocked():
    with TestClient(app) as client:
        first = _register_via_web(client, "owner-web@example.test")
        second = _register_via_web(client, "second-web@example.test")

    assert first.status_code == 303
    assert first.headers["location"] == "/dashboard"
    assert second.status_code == 400
    assert "Регистрация закрыта" in second.text


def test_legacy_non_owner_session_cannot_access_owner_state(db):
    owner = register_user(db, "owner@example.test", "strong-password", display_name="Owner")
    non_owner = User(
        email="legacy@example.test",
        password_hash=hash_password("strong-password"),
        display_name="Legacy",
        is_active=1,
    )
    db.add(non_owner)
    db.commit()
    db.refresh(non_owner)

    assert owner.id != non_owner.id
    assert owner_user(db).id == owner.id


def test_current_user_from_session_rejects_legacy_non_owner(db):
    owner = register_user(db, "owner@example.test", "strong-password", display_name="Owner")
    non_owner = User(
        email="legacy@example.test",
        password_hash=hash_password("strong-password"),
        display_name="Legacy",
        is_active=1,
    )
    db.add(non_owner)
    db.commit()
    db.refresh(non_owner)

    class FakeRequest:
        session = {"user_id": non_owner.id}

    assert owner.id != non_owner.id
    assert current_user_from_session(FakeRequest(), db) is None


def test_owner_user_ignores_inactive_or_non_credentialed_test_smoke_users(db):
    db.add_all(
        [
            User(
                email="test-old@example.test",
                password_hash=hash_password("strong-password"),
                display_name="Historical Test",
                is_active=0,
            ),
            User(
                email="smoke-old@example.test",
                password_hash=None,
                display_name="Historical Smoke",
                is_active=1,
            ),
        ]
    )
    db.commit()

    owner = register_user(db, "owner@example.test", "strong-password", display_name="Owner")

    assert owner_user(db).id == owner.id
    assert active_credentialed_test_smoke_users(db) == []


def test_active_credentialed_test_smoke_users_detects_unsafe_lower_id_user(db):
    unsafe = User(
        email="test-unsafe@example.test",
        password_hash=hash_password("strong-password"),
        display_name="Unsafe Test",
        is_active=1,
    )
    db.add(unsafe)
    db.commit()
    db.refresh(unsafe)

    owner = User(
        email="owner@example.test",
        password_hash=hash_password("strong-password"),
        display_name="Owner",
        is_active=1,
    )
    db.add(owner)
    db.commit()

    unsafe_users = active_credentialed_test_smoke_users(db)
    assert [user.id for user in unsafe_users] == [unsafe.id]
    assert owner_user(db).id == unsafe.id


def test_steam_openid_callback_without_owner_session_does_not_create_uncontrolled_user(db, monkeypatch):
    with SessionLocal() as session:
        register_user(session, "owner@example.test", "strong-password", display_name="Owner")
    monkeypatch.setattr("app.web.routes.validate_openid_callback", lambda _params: ("76561198056634139", None))

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/steam/callback?openid.mode=id_res")

    assert response.status_code == 303
    assert _app_db_count(User) == 1
    assert _app_db_count(SteamAccount) == 0
    assert _app_db_count(ImportJob) == 0


def test_steam_import_settings_requires_owner_session():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/settings/imports")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_steam_auth_start_requires_owner_session():
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/auth/steam")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_steam_import_pull_all_without_owner_session_does_not_create_job():
    with TestClient(app, follow_redirects=False) as client:
        login_page = client.get("/login")
        response = client.post(
            "/settings/imports/pull-all",
            data={"csrf_token": _csrf_from(login_page)},
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert _app_db_count(ImportJob) == 0


def test_owner_session_can_link_steam_to_owner(monkeypatch):
    monkeypatch.setattr("app.web.routes.validate_openid_callback", lambda _params: ("76561198056634139", None))

    with TestClient(app, follow_redirects=False) as client:
        _register_via_web(client, "owner-steam@example.test")
        response = client.get("/auth/steam/callback?openid.mode=id_res")

    assert response.status_code == 303
    account = _app_db_one(SteamAccount)
    job = _app_db_one(ImportJob)
    with SessionLocal() as session:
        owner = owner_user(session)
        assert owner is not None
        owner_id = owner.id
    assert account.user_id == owner_id
    assert job.steam_account_id == account.id


def test_api_token_represents_owner_operator_without_creating_users(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "owner-token")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.get("/api/matches", headers={"Authorization": "Bearer owner-token"})
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert _app_db_count(User) == 0


def test_owned_data_chain_helpers_deny_cross_owner_rows(db):
    owner = register_user(db, "owner@example.test", "strong-password", display_name="Owner")
    other = User(
        email="other@example.test",
        password_hash=hash_password("strong-password"),
        display_name="Other",
        is_active=1,
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    job = ImportJob(
        provider="steam",
        job_type="demo_import_orchestration",
        status="completed",
        user_id=owner.id,
        requested_payload_json="{}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    match = Match(
        user_id=owner.id,
        import_job_id=job.id,
        source="steam_history",
        external_match_id="CSGO-owner-chain",
        demo_file="/tmp/owner.dem",
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    artifact = DemoParseArtifact(
        match_id=match.id,
        import_job_id=job.id,
        parser_name="fixture-parser",
        payload_version="parser-artifact-v1",
        status="completed",
        source_demo_file=match.demo_file,
        event_counts_json="{}",
        confidence_json="{}",
        data_gaps_json="[]",
        payload_json="{}",
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    snapshot = create_metric_snapshot(
        db,
        match_id=match.id,
        player_key="steam:owner",
        source="parser_artifact",
        source_parser_artifact_id=artifact.id,
        metrics={"kills": 10},
        confidence_baseline={"metrics": {"kills": "trusted"}},
    )
    report = CoachReport(
        user_id=owner.id,
        source_metric_snapshot_id=snapshot.id,
        matches_count=1,
        report_type="ai_coach",
        source_ref="fixture",
        report_markdown="Owner report",
        report_json="{}",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    assert get_owned_import_job(db, user_id=owner.id, job_id=job.id).id == job.id
    assert get_owned_match(db, user_id=owner.id, match_id=match.id).id == match.id
    assert get_owned_parse_artifact(db, user_id=owner.id, artifact_id=artifact.id).id == artifact.id
    assert get_owned_metric_snapshot(db, user_id=owner.id, snapshot_id=snapshot.id).id == snapshot.id
    assert get_owned_coach_report(db, user_id=owner.id, report_id=report.id).id == report.id

    assert get_owned_import_job(db, user_id=other.id, job_id=job.id) is None
    assert get_owned_match(db, user_id=other.id, match_id=match.id) is None
    assert get_owned_parse_artifact(db, user_id=other.id, artifact_id=artifact.id) is None
    assert get_owned_metric_snapshot(db, user_id=other.id, snapshot_id=snapshot.id) is None
    assert get_owned_coach_report(db, user_id=other.id, report_id=report.id) is None
