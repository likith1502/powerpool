"""
conftest.py — shared pytest fixtures for all backend tests.

Isolation strategy:
  * DB_PATH is force-set to the test path BEFORE any backend module loads,
    overriding any value already present in the shell environment or a .env
    file.  Using os.environ[] (not setdefault) makes this guarantee firm.
  * The session-scoped _seed_test_db fixture seeds once and is reused by the
    session-scoped client fixture (fast — suitable for most tests).
  * The function-scoped fresh_client fixture calls POST /demo/reseed before
    each test that needs a guaranteed clean state (zero nudges, zero points),
    eliminating the session-ordering dependency that caused the previous
    test_nudge_send_specific_nudge to always be skipped.
  * The test DB file is deleted after the session to keep the working tree
    clean and prevent accidental commits.

To use the shared client in a new test file:
    def test_something(client): ...

To use a guaranteed-fresh client:
    def test_something(fresh_client): ...
"""
import os
import pathlib
import pytest

# ── Force the backend at a throwaway DB before any backend code loads ──────────
# os.environ[] (not setdefault) overrides any existing DB_PATH from the shell
# or from a .env file, so the test suite can never reach the dev database.
TEST_DB = "data/test_powerpool.db"
os.environ["DB_PATH"] = TEST_DB

# ── Ensure the data/ directory exists (created by db.py anyway, but be safe) ──
pathlib.Path(TEST_DB).parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _seed_test_db():
    """Seed a fresh DB once per test session. Teardown deletes the file."""
    from backend.seed_mock import seed
    from backend.db import init_db
    init_db()
    seed()
    yield
    # Teardown: remove the test DB so it is never accidentally committed.
    db = pathlib.Path(TEST_DB)
    if db.exists():
        db.unlink()


@pytest.fixture(scope="session")
def client(_seed_test_db):
    """A FastAPI TestClient that shares the seeded session DB.

    Use this for tests that do not depend on a pristine nudge/points state.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


@pytest.fixture()
def fresh_client(_seed_test_db):
    """A FastAPI TestClient backed by a freshly reseeded database.

    Use this when a test must start from a known-clean state (e.g. zero nudges,
    zero points) regardless of what earlier tests have done.  Reseeding is done
    through POST /demo/reseed so no test file imports seed_mock directly.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    c = TestClient(app)
    # Reset to a clean seed state: 80 HH, 275 appliances, 0 nudges, 0 points
    resp = c.post("/demo/reseed")
    assert resp.status_code == 200, f"Reseed failed: {resp.text}"
    return c
