import time
from typing import Callable, Iterable, Optional, Set, Type
import httpx

from .exceptions import (
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    BluebeamError,
)

def is_transient_http_status(status: int, retry_statuses: Set[int]) -> bool:
    return status in retry_statuses

def raise_for_status_mapped(resp: httpx.Response) -> None:
    """Map HTTP errors to SDK exceptions."""
    if 200 <= resp.status_code < 300:
        return
    if resp.status_code in (401,):
        raise AuthorizationError("Unauthorized (401)")
    if resp.status_code in (403,):
        raise AuthorizationError("Forbidden (403)")
    if resp.status_code == 404:
        raise NotFoundError("Not Found (404)")
    if resp.status_code == 429:
        raise RateLimitError("Too Many Requests (429)")
    if 500 <= resp.status_code < 600:
        raise ServerError(f"Server error ({resp.status_code})")
    # Fallback
    resp.raise_for_status()

def retry(
    *,
    max_retries: int,
    backoff_base: float,
    retry_statuses: Set[int],
    retry_on_exceptions: Iterable[Type[BaseException]] = (httpx.TransportError,),
):
    """Simple retry decorator for transient errors."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except retry_on_exceptions as ex:
                    attempt += 1
                    if attempt > max_retries:
                        raise ServerError(f"Network/transport error after retries: {ex}") from ex
                    time.sleep(backoff_base * (2 ** (attempt - 1)))
                except RateLimitError as ex:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    # Basic backoff for 429; honor Retry-After if present
                    resp: Optional[httpx.Response] = getattr(ex, "response", None)  # type: ignore
                    delay = backoff_base * (2 ** (attempt - 1))
                    if resp is not None:
                        ra = resp.headers.get("Retry-After")
                        if ra:
                            try:
                                delay = max(delay, float(ra))
                            except ValueError:
                                pass
                    time.sleep(delay)
                except ServerError:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    time.sleep(backoff_base * (2 ** (attempt - 1)))
        return wrapper
    return decorator
