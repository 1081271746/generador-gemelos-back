from sqlalchemy import create_engine, inspect

from app.database.base import Base
from app import models


def test_all_tables_have_foreign_keys_and_portable_json():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "users", "scenarios", "negotiations", "messages", "analyses",
        "negotiator_profiles", "events",
    }
    assert inspector.get_foreign_keys("events")
    assert models.Message.__table__.constraints
