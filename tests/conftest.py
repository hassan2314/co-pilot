import os

os.environ["LLM_PROVIDER"] = "local"
os.environ["DATABASE_URL"] = "postgresql://acme:acme@127.0.0.1:5432/docs_test"
os.environ["DB_CONNECT_TIMEOUT"] = "3"
os.environ["MAX_DOCUMENTS"] = "50"
os.environ["MAX_UPLOAD_BYTES"] = str(8 * 1024 * 1024)

import psycopg
import pytest

ADMIN_URL = "postgresql://acme:acme@127.0.0.1:5432/postgres"
TEST_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def postgres():
    try:
        with psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'docs_test'")
                if cur.fetchone() is None:
                    cur.execute("CREATE DATABASE docs_test OWNER acme")
    except Exception as exc:
        pytest.skip(f"Postgres is not available: {exc}")
    return TEST_URL


@pytest.fixture()
def client(postgres):
    from fastapi.testclient import TestClient

    from agents.tools.docs import clear_index
    from app.main import app

    with TestClient(app) as test_client:
        cleared = clear_index()
        assert cleared["status"] == "success", cleared
        yield test_client
        clear_index()
