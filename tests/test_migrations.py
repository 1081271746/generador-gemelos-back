import os
import subprocess

from sqlalchemy import create_engine, inspect


def test_migration_upgrade_and_downgrade(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(["python", "-m", "alembic", "upgrade", "head"], env=env, check=True)
    engine = create_engine(url)
    assert "users" in inspect(engine).get_table_names()
    engine.dispose()
    subprocess.run(["python", "-m", "alembic", "downgrade", "base"], env=env, check=True)


def test_upgrade_preserves_existing_records_and_backfills_snapshot(tmp_path):
    from sqlalchemy import text
    import json
    url = f"sqlite:///{tmp_path / 'existing.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(["python", "-m", "alembic", "upgrade", "0001"], env=env, check=True)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users VALUES (1,'old_user','old@example.com','invalid-test-hash',1,'2026-01-01')"))
        connection.execute(text("INSERT INTO scenarios VALUES (1,1,'Old title','Description','Context','Goal','Supplier','Margin','Limit',1,'2026-01-01')"))
        connection.execute(text("INSERT INTO negotiations VALUES (1,1,1,'active','2026-01-01',NULL)"))
        connection.execute(text("INSERT INTO messages VALUES (1,1,'user','Original offer','2026-01-01')"))
    subprocess.run(["python", "-m", "alembic", "upgrade", "head"], env=env, check=True)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT content FROM messages WHERE id=1")) == "Original offer"
        assert connection.scalar(text("SELECT token_version FROM users WHERE id=1")) == 0
        snapshot = json.loads(connection.scalar(text("SELECT scenario_snapshot FROM negotiations WHERE id=1")))
        assert snapshot["title"] == "Old title"
    engine.dispose()
