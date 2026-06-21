import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")

_store: dict[str, tuple[float, object]] = {}


async def cached(key: str, ttl: float, loader: Callable[[], Awaitable[T]]) -> T:
    """In-process TTL cache. Collapses repeated reads of rarely-changing data
    (products/categories) so a burst of concurrent requests doesn't hammer the DB."""
    now = time.monotonic()
    entry = _store.get(key)
    if entry and entry[0] > now:
        return entry[1]  # type: ignore[return-value]

    value = await loader()
    _store[key] = (now + ttl, value)
    return value


def invalidate(prefix: str = "") -> None:
    if not prefix:
        _store.clear()
        return
    for key in [k for k in _store if k.startswith(prefix)]:
        _store.pop(key, None)
