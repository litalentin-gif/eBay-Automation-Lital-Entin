"""
Retry Utility - Graceful Recovery for Unstable Environments
===========================================================
Use @retry_on_failure on any function that might fail due to
network issues, dynamic page loading, or transient UI glitches.
"""

import time
import logging
import functools
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_attempts: int = 3,
    backoff_factor: float = 1.5,
    exceptions: tuple = (Exception,),
    screenshot_page=None
):
    """
    Decorator: retries a function up to max_attempts times.
    Wait time grows with backoff_factor (exponential backoff).

    Args:
        max_attempts: how many total tries (including first)
        backoff_factor: multiplier for wait time between retries
        exceptions: which exception types to catch and retry
        screenshot_page: if provided, take screenshot on final failure
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            wait_time = 1.0
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(
                            f"[Retry] ✅ '{func.__name__}' succeeded on attempt {attempt}"
                        )
                    return result

                except exceptions as e:
                    logger.warning(
                        f"[Retry] ⚠️  '{func.__name__}' attempt {attempt}/{max_attempts} "
                        f"failed: {type(e).__name__}: {e}"
                    )
                    if attempt == max_attempts:
                        logger.error(
                            f"[Retry] ❌ '{func.__name__}' EXHAUSTED all {max_attempts} attempts."
                        )
                        raise

                    logger.info(f"[Retry] ⏳ Waiting {wait_time:.1f}s before next attempt...")
                    time.sleep(wait_time)
                    wait_time *= backoff_factor

        return wrapper
    return decorator


class RetryContext:
    """
    Inline retry helper (use when you can't use decorator).

    Example:
        with RetryContext(max_attempts=3) as ctx:
            while ctx.should_retry():
                try:
                    do_something()
                    ctx.success()
                except Exception as e:
                    ctx.record_failure(e)
    """

    def __init__(self, max_attempts: int = 3, backoff_factor: float = 1.5):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self._attempt = 0
        self._last_error = None
        self._done = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def should_retry(self) -> bool:
        if self._done:
            return False
        if self._attempt >= self.max_attempts:
            if self._last_error:
                raise self._last_error
            return False
        self._attempt += 1
        return True

    def success(self):
        self._done = True

    def record_failure(self, error: Exception):
        self._last_error = error
        wait = (self.backoff_factor ** (self._attempt - 1))
        logger.warning(f"[RetryContext] Attempt {self._attempt} failed: {error}. Waiting {wait:.1f}s")
        time.sleep(wait)
