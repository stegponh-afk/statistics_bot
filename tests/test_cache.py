from app.cache import MemoryCache
from tests.fakes import FakeClock


async def test_ttl_expiry(clock: FakeClock, cache: MemoryCache):
    await cache.set("k", "v", ttl=10)
    assert await cache.get("k") == "v"
    clock.advance(11)
    assert await cache.get("k") is None


async def test_incr_applies_ttl_only_on_creation(clock: FakeClock, cache: MemoryCache):
    assert await cache.incr("c", ttl=10) == 1
    clock.advance(5)
    assert await cache.incr("c", ttl=10) == 2
    clock.advance(6)
    assert await cache.incr("c", ttl=10) == 1


async def test_set_if_absent(cache: MemoryCache):
    assert await cache.set_if_absent("x", "1", ttl=5) is True
    assert await cache.set_if_absent("x", "2", ttl=5) is False


async def test_sets_distinguish_unknown_from_empty(cache: MemoryCache):
    assert await cache.smembers("s") is None
    await cache.sadd("s", ttl=5)
    assert await cache.smembers("s") == set()
    await cache.sadd("s", "1", "2")
    assert await cache.smembers("s") == {"1", "2"}
