"""Fixed-window rate limiting on top of Cache.incr."""

import time
from dataclasses import dataclass

from app.cache import Cache


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int  # seconds until the window resets (0 when allowed)


async def check(
    cache: Cache, bucket: str, limit: int, window: int = 60, now: float | None = None
) -> Decision:
    now = time.time() if now is None else now
    slot = int(now // window)
    count = await cache.incr(f"rl:{bucket}:{slot}", ttl=window)
    if count <= limit:
        return Decision(True, 0)
    return Decision(False, max(1, int((slot + 1) * window - now)))
