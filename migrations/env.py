import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from sentinelops.persistence import Base

config = context.config


def apply(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = async_engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(apply)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    apply(config.attributes["connection"])
else:
    asyncio.run(run())
