"""Async mutex/lock utilities for thread-safe operations."""

import asyncio
from typing import TypeVar

T = TypeVar("T")


class AsyncMutex:
    """Async mutex for protecting critical sections.

    Usage:
        mutex = AsyncMutex()
        async with mutex:
            # Protected code here
            pass
    """

    def __init__(self) -> None:
        """Initialize the mutex with an asyncio Lock."""
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncMutex":
        """Acquire the lock."""
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Release the lock."""
        self._lock.release()

    @property
    def locked(self) -> bool:
        """Check if the lock is currently held."""
        return self._lock.locked()


class AsyncOnce:
    """Ensure an async operation runs only once.

    Usage:
        once = AsyncOnce()
        result = await once.call(async_factory)
    """

    def __init__(self) -> None:
        """Initialize with no result."""
        self._lock = asyncio.Lock()
        self._result: T | None = None
        self._called = False

    async def call(self, factory: "asyncio.Coroutine[None, None, T]") -> T:
        """Call the factory once and cache the result.

        Args:
            factory: An async callable that produces the result.

        Returns:
            The cached result from the first call.
        """
        if self._called:
            return self._result  # type: ignore

        async with self._lock:
            if self._called:
                return self._result  # type: ignore

            self._result = await factory
            self._called = True
            return self._result
