"""Pytest setup: every test gets an isolated SQLite database.

Env vars are set here at import time — before any app module is imported —
because app.config reads them once at import.
"""
import os

TEST_DB = "/tmp/careloop_test.db"
os.environ["CARELOOP_DB_PATH"] = TEST_DB
os.environ["CARELOOP_LLM_PROVIDER"] = "demo"
os.environ["CARELOOP_SCHEDULER_INTERVAL"] = "3600"  # don't tick during tests

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    from app import db
    db.init_db()
    yield
