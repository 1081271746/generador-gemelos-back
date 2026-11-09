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
