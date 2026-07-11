# BUGFIX-001 Coach Runtime Failure Diagnosis

Дата: 2026-07-03.

Режим: diagnosis-only. Код, тесты, существующая документация и DB не изменялись. Live AI calls, live Steam calls, production import/parser jobs не запускались.

## RESULT

DIAGNOSED

## Runtime Symptom

В браузере authenticated GET `/coach` возвращает `500 Internal Server Error`.

Runtime service:

```text
jc-coach.service active/running
uvicorn pid 50582
/opt/jc-coach/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Relevant logs:

- primary: `journalctl -u jc-coach.service --no-pager`
- nginx access/error if needed: `/var/log/nginx/jcnodex.access.log`, `/var/log/nginx/jcnodex.error.log`

## Exact Error / Stack Trace

From `journalctl -u jc-coach.service`:

```text
GET /coach HTTP/1.1" 500 Internal Server Error
jinja2.exceptions.UndefinedError: 'coach_ui' is undefined
```

Relevant stack location:

```text
File "/opt/jc-coach/app/templates/coach.html", line 28, in block 'content'
  <span>{{ coach_ui.current.status if coach_ui.current.available else "empty" }}</span>
jinja2.exceptions.UndefinedError: 'coach_ui' is undefined
```

The stack also shows the running endpoint frame at:

```text
File "/opt/jc-coach/app/web/routes.py", line 287, in coach_page
  parse_overview = _demo_parse_overview(db, len(matches))
...
TemplateResponse(...)
```

That stack corresponds to old in-memory `coach_page` code that renders `coach.html` without passing `coach_ui`.

## Root Cause

Root cause: deployment/restart mismatch.

The running uvicorn process was started before Stage 9 Python route changes:

```text
uvicorn pid 50582 started: Fri Jul 3 01:52:35 2026
Stage 9 commit: a8192f4 2026-07-03 20:25:51 +0300 Make coach UI action-first
```

After Stage 9, `app/templates/coach.html` on disk references `coach_ui`, and current `app/web/routes.py` on disk now adds `coach_ui` to the template context.

But the already-running uvicorn process still has the old imported `app/web/routes.py` module in memory. Jinja loads/renders the updated template from disk, while the running route handler still builds the old context without `coach_ui`. This produces:

```text
'coach_ui' is undefined
```

Failure location:

- route helper: no logic failure in current source; running process uses stale route code.
- template: updated template requires `coach_ui`.
- auth/session: not root cause; the 500 occurs after successful login and authenticated `/coach`.
- AI report JSON: not root cause.
- recommendation progress: not root cause.
- latest match summary: not root cause.
- missing/None data: not root cause.
- deployment/restart issue: yes, root cause.

## Why Existing Tests Missed It

`tests/test_coach_first_ui.py` imports `app.main` / `app.web.routes` fresh inside the pytest process, so tests run current source code from disk:

- current `coach_page()` includes `coach_ui`;
- current `coach.html` expects `coach_ui`;
- the pair is consistent.

The browser/runtime process was different:

- uvicorn service was already running from before Stage 9;
- Python route module stayed old in memory;
- template file was updated on disk;
- route/template pair became inconsistent only in the long-running service.

Existing tests verify source correctness, not deployment freshness. They do not check that `jc-coach.service` was restarted after Python code changes, and they do not smoke-test the already-running production service with an authenticated session.

## Minimal Fix Plan

1. Restart the app service so uvicorn imports the Stage 9 `app/web/routes.py` code:

```bash
sudo systemctl restart jc-coach.service
```

2. Confirm process start time is after Stage 9 commit:

```bash
systemctl status jc-coach.service --no-pager
ps -p <uvicorn_pid> -o pid,lstart,cmd
```

3. Re-open `/coach` in browser with existing authenticated session.

4. Verify logs have no new `jinja2.exceptions.UndefinedError: 'coach_ui' is undefined`.

5. Verify production DB SHA before/after a simple `/coach` GET if checking read-only behavior.

No code repair appears required for this specific failure. If the service restart reveals a new error, diagnose that separately from BUGFIX-001.

## Required Regression Test

Add an ops/runtime freshness check, not just a unit/TestClient test.

Minimum regression procedure:

1. After any commit that changes Python route code or templates, restart `jc-coach.service`.
2. Run an authenticated runtime smoke GET against the actual service `/coach`.
3. Assert HTTP 200 and marker text:

```text
Current tracked recommendation
```

4. Assert service logs do not contain:

```text
jinja2.exceptions.UndefinedError
```

If automated without mutating production DB, avoid login POST because login updates `last_login_at`. Use a test/staging runtime DB, or add a safe smoke fixture that creates an authenticated session in `APP_ENV=test`.

Code-level regression test to add later:

- a template-context contract test that calls the current `/coach` route through TestClient and asserts `coach_ui` markers;
- already partially covered by `tests/test_coach_first_ui.py`;
- not sufficient for stale service process detection.

Ops-level regression test:

- verify running process start time is newer than the last deployed commit/template mtime before manual browser validation.

## Production DB Check

Initial DB SHA observed during diagnosis:

```text
c3fdb47427297a9f0786be423b6cbb0c04ed1c0b4a2a9a13add24098134f61e1
```

Note: this differs from Stage 9 review SHA because the user/browser login at `20:28:05` likely updated `users.last_login_at`.

Safe unauthenticated GET `/coach` check:

```text
HTTP=303 http://127.0.0.1:8010/login
SHA_BEFORE=c3fdb47427297a9f0786be423b6cbb0c04ed1c0b4a2a9a13add24098134f61e1
SHA_AFTER=c3fdb47427297a9f0786be423b6cbb0c04ed1c0b4a2a9a13add24098134f61e1
```

That safe check did not mutate production DB.

Later during the same diagnosis window, runtime logs show external browser activity:

```text
20:44:39 POST /login HTTP/1.1" 303 See Other
20:44:45 GET /coach HTTP/1.1" 500 Internal Server Error
```

After that activity the DB file mtime and SHA changed:

```text
mtime: 2026-07-03 20:44:39.263652678 +0300
SHA: 01c2c10b87e1c1f14f2509c14666ec8830836de0532b0b41d5b0374663d2917f
```

This change is consistent with login updating session/user runtime state, not with the safe unauthenticated diagnostic GET. The diagnosis pass itself did not intentionally perform authenticated login, import, parser, Steam, AI, or DB mutation commands.

## Safety Notes

- No code changes were made.
- No tests were changed.
- No existing docs were changed.
- No DB writes were intentionally performed.
- No live AI calls were run.
- No live Steam calls were run.
- No production import/parser jobs were run.
- No commit was made.

## Can Proceed To Repair

yes

Recommended repair action: restart `jc-coach.service` and verify `/coach`. Only if a new stack trace appears after restart should a code-level bugfix be started.
