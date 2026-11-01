from sqlalchemy import create_engine

from alembic import context
from splitbill.config import Settings
from splitbill.models import Base

config = context.config


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif "connection" in config.attributes:
    run_migrations(config.attributes["connection"])
else:
    engine = create_engine(Settings().database_url)
    with engine.connect() as connection:
        run_migrations(connection)
    engine.dispose()
