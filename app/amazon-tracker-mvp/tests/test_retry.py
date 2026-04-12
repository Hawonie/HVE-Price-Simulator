"""Unit tests for retry_with_backoff utility."""

import asyncio
import logging

import pytest

from app.utils.retry import retry_with_backoff


async def test_succeeds_on_first_attempt():
    """Should return the result immediately when no exception occurs."""

    async def ok():
        return "hello"

    result = await retry_with_backoff(coro_factory=ok, max_retries=3)
    assert result == "hello"


async def test_retries_then_succeeds():
    """Should retry on failure and return the result once it succeeds."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("transient error")
        return "recovered"

    result = await retry_with_backoff(
        coro_factory=flaky,
        max_retries=3,
        base_delay=0.01,  # keep tests fast
        operation_name="flaky_op",
    )
    assert result == "recovered"
    assert call_count == 3


async def test_raises_after_all_retries_exhausted():
    """Should raise the last exception when all retries are exhausted."""
    call_count = 0

    async def always_fail():
        nonlocal call_count
        call_count += 1
        raise ValueError(f"fail #{call_count}")

    with pytest.raises(ValueError, match="fail #3"):
        await retry_with_backoff(
            coro_factory=always_fail,
            max_retries=3,
            base_delay=0.01,
        )
    assert call_count == 3


async def test_single_retry_raises_immediately():
    """With max_retries=1, should not retry at all."""
    call_count = 0

    async def fail_once():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await retry_with_backoff(
            coro_factory=fail_once,
            max_retries=1,
            base_delay=0.01,
        )
    assert call_count == 1


async def test_exponential_backoff_delays(monkeypatch):
    """Verify that sleep is called with the correct exponential delays."""
    recorded_delays: list[float] = []

    async def fake_sleep(delay):
        recorded_delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    call_count = 0

    async def fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RuntimeError("err")
        return "done"

    result = await retry_with_backoff(
        coro_factory=fail_twice,
        max_retries=3,
        base_delay=2.0,
        operation_name="delay_test",
    )
    assert result == "done"
    # attempt 1 fails → delay = 2.0 * 2^0 = 2.0
    # attempt 2 fails → delay = 2.0 * 2^1 = 4.0
    assert recorded_delays == [2.0, 4.0]


async def test_logs_warning_on_retry(caplog):
    """Should log WARNING for each retry attempt."""
    call_count = 0

    async def fail_then_ok():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("oops")
        return "ok"

    with caplog.at_level(logging.WARNING, logger="app.utils.retry"):
        await retry_with_backoff(
            coro_factory=fail_then_ok,
            max_retries=3,
            base_delay=0.01,
            operation_name="log_test",
        )

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "log_test attempt 1 failed" in warning_records[0].message


async def test_logs_error_on_final_failure(caplog):
    """Should log ERROR when all retries are exhausted."""

    async def always_fail():
        raise RuntimeError("permanent")

    with caplog.at_level(logging.ERROR, logger="app.utils.retry"):
        with pytest.raises(RuntimeError):
            await retry_with_backoff(
                coro_factory=always_fail,
                max_retries=2,
                base_delay=0.01,
                operation_name="err_test",
            )

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert "err_test failed after 2 attempts" in error_records[0].message
