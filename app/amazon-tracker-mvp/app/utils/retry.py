"""Retry utility with exponential backoff for async operations."""

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    coro_factory: Callable[[], Coroutine[Any, Any, Any]],
    max_retries: int = 3,
    base_delay: float = 2.0,
    operation_name: str = "operation",
) -> Any:
    """Execute an async operation with exponential backoff retry.

    Args:
        coro_factory: A callable that returns a new coroutine on each invocation.
        max_retries: Maximum number of attempts before giving up.
        base_delay: Base delay in seconds. Actual delay is base_delay * 2^(attempt-1).
        operation_name: Human-readable name for logging.

    Returns:
        The result of the coroutine on success.

    Raises:
        Exception: The last exception if all retries are exhausted.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            if attempt == max_retries:
                logger.error(
                    "%s failed after %d attempts: %s",
                    operation_name,
                    max_retries,
                    e,
                )
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "%s attempt %d failed: %s. Retrying in %ss...",
                operation_name,
                attempt,
                e,
                delay,
            )
            await asyncio.sleep(delay)
