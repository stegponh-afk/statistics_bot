import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST")

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.cache import MemoryCache  # noqa: E402
from app.database import models  # noqa: E402, F401
from app.database.base import Base  # noqa: E402
from tests.fakes import FakeBot, FakeClock  # noqa: E402


@pytest.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def cache(clock: FakeClock) -> MemoryCache:
    return MemoryCache(clock=clock)


@pytest.fixture
def bot() -> FakeBot:
    return FakeBot()
