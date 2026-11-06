import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./_unused_test.db")
os.environ["SEED_DEMO_DATA"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import get_db, init_db, make_engine
from app.main import app
from app.seed import DEMO_PASSWORD, seed
from app.services.knowledge_index import index_documents


@pytest.fixture()
def SessionTest(tmp_path):
    """A fresh SQLite database per test (the audit table is append-only, so no cleanup)."""
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as db:
        seed(db)
        index_documents(db)
    yield Session
    engine.dispose()


@pytest.fixture()
def db(SessionTest):
    with SessionTest() as s:
        yield s


@pytest.fixture()
def client(SessionTest):
    def override():
        with SessionTest() as s:
            yield s
    app.dependency_overrides[get_db] = override
    yield TestClient(app)  # no context manager: skips the production lifespan
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client):
    def _login(username: str) -> dict:
        r = client.post("/api/auth/login", data={"username": username, "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login
