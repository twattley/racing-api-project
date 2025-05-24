from asyncio import current_task
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from api_helpers.config import config


class DatabaseSessionManager:
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_maker = None
        self.session = None

    def init_db(self):
        if self.engine is None:
            self.engine = create_async_engine(
                url=self._create_db_url(config),
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=False,
            )

            self.session_maker = async_sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

            self.session = async_scoped_session(
                self.session_maker, scopefunc=current_task
            )

    def _create_db_url(self, config) -> str:
        return (
            "postgresql"
            + "+"
            + "asyncpg"
            + "://"
            + config.db_user
            + ":"
            + config.db_password
            + "@"
            + config.db_host
            + ":"
            + config.db_port
            + "/"
            + config.db_name
        )

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
