class BluebeamError(Exception):
    """Base SDK error."""


class AuthenticationError(BluebeamError):
    """Invalid credentials / token exchange / refresh failures."""


class AuthorizationError(BluebeamError):
    """403/401 when token is missing or lacks scope."""


class NotFoundError(BluebeamError):
    """404 for resources like sessions/files not found."""


class RateLimitError(BluebeamError):
    """429 Too Many Requests (rate-limited)."""


class ServerError(BluebeamError):
    """5xx errors we couldn't recover from after retries."""


class UnsupportedOperationError(BluebeamError):
    """Documented gaps or unimplemented endpoints."""
