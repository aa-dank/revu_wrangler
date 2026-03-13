from .client import BluebeamClient
from .exceptions import (
    BluebeamError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnsupportedOperationError,
)

# Convenience aliases for the rebranded package
RevuWranglerClient = BluebeamClient
RevuWranglerError = BluebeamError

__all__ = [
    "BluebeamClient",
    "RevuWranglerClient",
    "BluebeamError",
    "RevuWranglerError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "UnsupportedOperationError",
]
