import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from inventory import cache as cache_module
from inventory.database import Base, get_db
from inventory.main import app as inventory_app


class FakeRedis:
    """Fake simples de Redis para testes isolados."""

    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return None
        self.values[key] = str(value)
        return True

    def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = str(value)
        return value

    def mget(self, keys):
        return [self.get(key) for key in keys]

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                deleted += 1
        return deleted


@pytest.fixture
def sqlite_engine():
    """Banco SQLite em memoria, isolado por teste."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Sessao SQLAlchemy vinculada ao banco efemero."""
    testing_session = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
    )
    session = testing_session()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def fake_redis():
    """Cache falso para evitar conexao com Redis real."""
    return FakeRedis()


@pytest.fixture
def test_app(monkeypatch, db_session, fake_redis):
    """Aplicacao FastAPI ligada ao banco e cache de teste."""
    def override_get_db():
        yield db_session

    inventory_app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(cache_module, "redis_client", fake_redis)

    yield inventory_app

    inventory_app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Cliente HTTP para testes de API."""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def frozen_time():
    """Relogio fixo em UTC para testes deterministas."""
    with freeze_time("2025-01-15 12:00:00+00:00") as clock:
        yield clock
