"""Shared pytest fixtures.

Root cause of "no such table: clinical_sessions": Base.metadata.create_all
normally runs inside app.main's FastAPI lifespan handler on startup, but
httpx's ASGITransport (used by every test's `client` fixture) talks to the
ASGI app directly and never fires lifespan startup/shutdown events. So any
model added after the last time someone actually ran the server (e.g. via
uvicorn) is missing from whatever sqlite file the tests point at.

This fixture creates any missing tables directly, the same way the lifespan
handler does, before every test. `Base.metadata.create_all` is idempotent
(checkfirst=True by default) — it only adds tables that don't exist yet, so
it never touches or drops existing rows (tests already rely on that, e.g.
test_clinical.py's per-test unique emails against a persistent dev db).
"""

import pytest

# Importing app.models (transitively, via app.main) registers every model
# class — including ClinicalSession, ClinicalQuestion, ClinicalAnswer, and
# RedFlagAlert — on Base.metadata before create_all runs below.
import app.models  # noqa: F401
from app.core.database import Base, engine


@pytest.fixture(autouse=True)
async def _ensure_db_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
