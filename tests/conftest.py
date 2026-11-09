import pytest
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.base import Base
from app.database.database import make_engine
from app.models import User, Scenario
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "test-access-signing-material-only-00000")
    monkeypatch.setattr(settings, "SERVICE_SECRET", "test-service-signing-material-only-0000")


@pytest.fixture
def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def owner(db):
    user = User(username="owner", email="owner@example.com", hashed_password=hash_password("test-password-long"))
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def scenario(db, owner):
    scenario = Scenario(user_id=owner.id, title="Contract", description="Supply contract",
        context="Annual supply", objective="Reduce cost", counterpart_role="Supplier",
        counterpart_goal="Increase margin", counterpart_limits="Minimum 100 per unit")
    db.add(scenario)
    db.commit()
    return scenario
