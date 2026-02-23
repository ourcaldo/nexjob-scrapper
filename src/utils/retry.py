"""
Retry utility with exponential backoff for HTTP requests.
"""

import time
import logging
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def retry_request(
    func,
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs,
):
    """
    Call func(*args, **kwargs) with exponential backoff retry.

    Args:
        func: Callable to invoke
        *args: Positional arguments to pass to func
        max_attempts: Total number of attempts before re-raising (default: 3)
        initial_delay: Seconds to wait before the second attempt (default: 1.0)
        backoff: Multiplier applied to delay on each failure (default: 2.0)
        exceptions: Exception types that trigger a retry (default: all exceptions)
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func on success

    Raises:
        The last exception raised by func after all attempts are exhausted
    """
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as exc:
            if attempt == max_attempts:
                logger.error(
                    f"{func.__name__} failed after {max_attempts} attempts: {exc}"
                )
                raise
            logger.warning(
                f"{func.__name__} attempt {attempt}/{max_attempts} failed: {exc}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= backoff
