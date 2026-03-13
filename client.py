from typing import List, Optional

import httpx

from .auth import AuthManager, OAuthToken
from .config import (
    REGION_BASE_URLS,
    DEFAULT_SCOPES,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_BASE,
    DEFAULT_RETRY_STATUS_CODES,
)
from .exceptions import AuthenticationError
from .sessions import SessionsAPI

class BluebeamClient:
    """
    Top-level SDK entry point.
    - Holds httpx.Client
    - Manages OAuth via AuthManager
    - Exposes SessionsAPI
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        region: str = "US",
        scopes: Optional[List[str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_base: float = DEFAULT_RETRY_BACKOFF_BASE,
    ):
        base_url = REGION_BASE_URLS.get(region.upper())
        if not base_url:
            raise ValueError(f"Unknown region '{region}'. Known: {sorted(REGION_BASE_URLS.keys())}")

        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or DEFAULT_SCOPES

        # Single shared HTTP client
        self.http = httpx.Client(timeout=timeout)
        # Auth manager
        self.auth = AuthManager(
            base_url=self.base_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scopes=self.scopes,
            http=self.http,
        )

        # Attach event hooks to auto-inject auth + client_id header
        def _auth_hook(request: httpx.Request):
            # Inject Authorization header (refresh if needed)
            if self.auth.token is None:
                raise AuthenticationError(
                    "No token set. Complete Authorization Code flow and set token with `set_token_from_code()` "
                    "or `set_token()`."
                )
            # If expired, refresh
            if self.auth.token.is_expired:
                self.auth.refresh_access_token()
            # Add headers
            request.headers.update(self.auth.get_auth_header())
            request.headers.setdefault("client_id", self.client_id)

        self.http_event_hooks = {"request": [_auth_hook]}
        # httpx.Client can't be mutated for hooks; recreate with hooks:
        self.http.close()
        self.http = httpx.Client(timeout=timeout, event_hooks=self.http_event_hooks)

        # APIs
        self.sessions = SessionsAPI(
            http=self.http,
            base_url=self.base_url,
            client_id=self.client_id,
            max_retries=max_retries,
            retry_backoff_base=retry_backoff_base,
            retry_statuses=DEFAULT_RETRY_STATUS_CODES,
        )

    # ---------- OAuth convenience ----------
    def get_authorization_url(self, *, state: Optional[str] = None) -> str:
        return self.auth.authorization_url(state=state)

    def set_token_from_code(self, code: str) -> OAuthToken:
        return self.auth.exchange_code_for_token(code)

    def set_token(self, *, access_token: str, refresh_token: Optional[str] = None, expires_in: int = 3600) -> OAuthToken:
        token = OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
        )
        self.auth.set_token(token)
        return token

    # ---------- Cleanup ----------
    def close(self) -> None:
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
