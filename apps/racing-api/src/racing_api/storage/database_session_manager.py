from asyncio import current_task
from typing import Any, AsyncIterator, Awaitable, Callable

from api_helpers.config import Config, config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSessionManager:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_maker = None
        self.session = None

    def init_db(self):
        if self.engine is None:
            connect_args = {"timeout": 10}

            # asyncpg uses 'prefer' as default, which works based on your tests
            # Only add ssl if explicitly set to 'require', 'disable', etc.
            if config.cloud_db_sslmode and config.cloud_db_sslmode != "None":
                connect_args["ssl"] = config.cloud_db_sslmode

            self.engine = create_async_engine(
                url=self._create_db_url(config),
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=False,
                connect_args=connect_args,
            )

            self.session_maker = async_sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            self.session = async_scoped_session(
                self.session_maker, scopefunc=current_task
            )

    def _create_db_url(self, config: Config) -> str:
        url = (
            "postgresql"
            + "+"
            + "asyncpg"
            + "://"
            + config.cloud_db_user
            + ":"
            + config.cloud_db_password
            + "@"
            + config.cloud_db_host
            + ":"
            + str(config.cloud_db_port)
            + "/"
            + config.cloud_db_name
        )
        return url

    async def close(self):
        if self.engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        if self.session is None:
            self.init_db()  # Initialize if not already done
        return self.session()


# Create a single instance
sessionmanager = DatabaseSessionManager()


async def database_session() -> AsyncIterator[AsyncSession]:
    session = sessionmanager.get_session()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def with_new_session(
    build_service: Callable[[AsyncSession], Any],
    coro_factory: Callable[[Any], Awaitable[Any]],
):
    """Run a service coroutine with a fresh AsyncSession.

    build_service: given an AsyncSession, return a constructed service instance.
    coro_factory: given that service instance, return an awaitable to execute.
    """
    if sessionmanager.session_maker is None:
        sessionmanager.init_db()
    async with sessionmanager.session_maker() as session:
        service = build_service(session)
        return await coro_factory(service)
