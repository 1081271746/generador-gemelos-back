from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.database.base import Base
from app import models


target_metadata = Base.metadata


def run_migrations():
    if context.is_offline_mode():
        context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
