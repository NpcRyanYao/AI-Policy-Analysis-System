import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import init_db
from app.main import create_app


@pytest.fixture(scope="session", autouse=True)
def _boot():
    get_settings.cache_clear()
    init_db(get_settings())


@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c
