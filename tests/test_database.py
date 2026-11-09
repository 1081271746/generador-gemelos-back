import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database.database import make_engine
from app.database.base import Base
from app import models


def test_foreign_keys_enforced(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO negotiations (user_id, scenario_id, status) VALUES (999,999,'active')"))
    engine.dispose()
