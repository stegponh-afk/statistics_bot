"""A tiny async key/value + set cache abstraction over Redis.

Services take a `Cache` instead of a Redis client so tests can plug in
`MemoryCache` (with a controllable clock) and never need a Redis server.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis


class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None: ...

    async def delete(self, *keys: str) -> None: ...

    async def incr(self, key: str, ttl: int | None = None) -> int:
        """Increments and returns the new value; ttl (if given) is applied
        only when the key is created by this call."""
        ...

    async def set_if_absent(self, key: str, value: str, ttl: int) -> bool:
        """SET NX EX — True if the key was set (i.e. it did not exist)."""
        ...

    async def sadd(self, key: str, *members: str, ttl: int | None = None) -> None: ...

    async def smembers(self, key: str) -> set[str] | None:
        """None if the set key does not exist at all (as opposed to empty)."""
        ...


class RedisCache:
    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def get(self, key: str) -> str | None:
        return await self._r.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._r.set(key, value, ex=ttl)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._r.delete(*keys)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        value = await self._r.incr(key)
        if ttl is not None and value == 1:
            await self._r.expire(key, ttl)
        return value

    async def set_if_absent(self, key: str, value: str, ttl: int) -> bool:
        return bool(await self._r.set(key, value, ex=ttl, nx=True))

    async def sadd(self, key: str, *members: str, ttl: int | None = None) -> None:
        if not members:
            # An empty set can't be represented in Redis; store a sentinel so
            # smembers() can tell "known empty" from "unknown".
            members = ("__empty__",)
        await self._r.sadd(key, *members)
        if ttl is not None:
            await self._r.expire(key, ttl)

    async def smembers(self, key: str) -> set[str] | None:
        members = await self._r.smembers(key)
        if not members:
            return None
        members.discard("__empty__")
        return set(members)


class MemoryCache:
    """In-process Cache for tests; `clock` lets a test advance time."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._data: dict[str, tuple[str | set[str], float | None]] = {}

    def _live(self, key: str) -> str | set[str] | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and self._clock() >= expires_at:
            del self._data[key]
            return None
        return value

    def _expiry(self, ttl: int | None) -> float | None:
        return None if ttl is None else self._clock() + ttl

    async def get(self, key: str) -> str | None:
        value = self._live(key)
        return value if isinstance(value, str) else None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._data[key] = (value, self._expiry(ttl))

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        current = self._live(key)
        if current is None:
            self._data[key] = ("1", self._expiry(ttl))
            return 1
        value = int(current) + 1
        self._data[key] = (str(value), self._data[key][1])
        return value

    async def set_if_absent(self, key: str, value: str, ttl: int) -> bool:
        if self._live(key) is not None:
            return False
        self._data[key] = (value, self._expiry(ttl))
        return True

    async def sadd(self, key: str, *members: str, ttl: int | None = None) -> None:
        current = self._live(key)
        existing = set(current) if isinstance(current, set) else set()
        existing.update(members)
        self._data[key] = (existing, self._expiry(ttl))

    async def smembers(self, key: str) -> set[str] | None:
        value = self._live(key)
        return set(value) if isinstance(value, set) else None
