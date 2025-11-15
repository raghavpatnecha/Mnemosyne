"""
Retry Logic Utilities

Provides automatic retry mechanisms for external API calls with exponential backoff.
Improves reliability by handling transient failures automatically.
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from openai import APIError, RateLimitError, APITimeoutError
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


def retry_on_api_error(max_attempts: int = None):
    """
    Decorator for retrying on API errors

    Retries on:
    - OpenAI APIError
    - Rate limit errors
    - Timeout errors

    Args:
        max_attempts: Maximum retry attempts (default: settings.RETRY_MAX_ATTEMPTS)

    Returns:
        Tenacity retry decorator
    """
    max_attempts = max_attempts or settings.RETRY_MAX_ATTEMPTS

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=2,
            max=30,
            exp_base=settings.RETRY_EXPONENTIAL_BASE
        ),
        retry=retry_if_exception_type((
            APIError,
            RateLimitError,
            APITimeoutError,
            ConnectionError,
            TimeoutError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


def retry_on_rate_limit(max_attempts: int = 5):
    """
    Decorator specifically for rate limit errors

    Uses longer backoff for rate limits

    Args:
        max_attempts: Maximum retry attempts (default: 5)

    Returns:
        Tenacity retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=2,  # Longer backoff for rate limits
            min=5,
            max=120,
            exp_base=2
        ),
        retry=retry_if_exception_type(RateLimitError),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


def retry_on_database_error(max_attempts: int = 3):
    """
    Decorator for retrying on database errors

    Retries on connection errors and deadlocks

    Args:
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Tenacity retry decorator
    """
    from sqlalchemy.exc import OperationalError, DBAPIError

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=10,
            exp_base=2
        ),
        retry=retry_if_exception_type((
            OperationalError,
            DBAPIError,
            ConnectionError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


class RetryableService:
    """
    Base class for services with built-in retry logic

    Services can extend this class to get automatic retry capabilities
    """

    @retry_on_api_error()
    async def call_api_with_retry(self, func, *args, **kwargs):
        """
        Call async function with automatic retry on API errors

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        return await func(*args, **kwargs)

    @retry_on_database_error()
    def call_db_with_retry(self, func, *args, **kwargs):
        """
        Call function with automatic retry on database errors

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        return func(*args, **kwargs)


# Example usage decorators

@retry_on_api_error(max_attempts=3)
async def example_api_call():
    """Example of using retry decorator on async function"""
    pass


@retry_on_database_error(max_attempts=3)
def example_db_call():
    """Example of using retry decorator on sync function"""
    pass
