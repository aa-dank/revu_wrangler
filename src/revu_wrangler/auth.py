import time
import urllib.parse
from typing import Dict, List, Optional

import httpx

from .config import (
    OAUTH_AUTHORIZE_PATH,
    OAUTH_TOKEN_PATH,
    DEFAULT_SCOPES,
)
from .exceptions import AuthenticationError

class OAuthToken:
    def __init__(
        self,
        access_token: str,
        token_type: str,
        expires_in: int,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        obtained_at: Optional[float] = None,
    ):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = int(expires_in)
        self.refresh_token = refresh_token
        self.scope = scope
        self.obtained_at = obtained_at or time.time()

    @property
    def is_expired(self) -> bool:
        # refresh a bit early (60s skew)
        return time.time() >= (self.obtained_at + max(0, self.expires_in - 60))

class AuthManager:
    """
    Handles OAuth2 Authorization Code flow + token refresh.
    Stores tokens in memory.
    """

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        http: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or DEFAULT_SCOPES
        self._http = http
        self._token: Optional[OAuthToken] = None

    def authorization_url(self, state: Optional[str] = None, extra_params: Optional[Dict[str, str]] = None) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
        }
        if state:
            params["state"] = state
        if extra_params:
            params.update(extra_params)
        return f"{self.base_url}{OAUTH_AUTHORIZE_PATH}?{urllib.parse.urlencode(params)}"

    def set_http_client(self, http: httpx.Client) -> None:
        self._http = http

    def set_token(self, token: OAuthToken) -> None:
        self._token = token

    @property
    def token(self) -> Optional[OAuthToken]:
        return self._token

    def exchange_code_for_token(self, code: str) -> OAuthToken:
        assert self._http is not None, "HTTP client not initialized"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        resp = self._http.post(f"{self.base_url}{OAUTH_TOKEN_PATH}", data=data)
        if resp.status_code != 200:
            raise AuthenticationError(f"Failed to obtain token: {resp.status_code} {resp.text}")
        payload = resp.json()
        tok = OAuthToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_in=payload.get("expires_in", 3600),
            refresh_token=payload.get("refresh_token"),
            scope=payload.get("scope"),
        )
        self._token = tok
        return tok

    def refresh_access_token(self) -> OAuthToken:
        assert self._http is not None, "HTTP client not initialized"
        if not self._token or not self._token.refresh_token:
            raise AuthenticationError("No refresh token available")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        resp = self._http.post(f"{self.base_url}{OAUTH_TOKEN_PATH}", data=data)
        if resp.status_code != 200:
            raise AuthenticationError(f"Failed to refresh token: {resp.status_code} {resp.text}")
        payload = resp.json()
        tok = OAuthToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "Bearer"),
            expires_in=payload.get("expires_in", 3600),
            refresh_token=payload.get("refresh_token", self._token.refresh_token),
            scope=payload.get("scope", self._token.scope if self._token else None),
        )
        self._token = tok
        return tok

    def get_auth_header(self) -> Dict[str, str]:
        if not self._token:
            raise AuthenticationError("No OAuth token set")
        if self._token.is_expired:
            self.refresh_access_token()
        assert self._token is not None
        return {"Authorization": f"Bearer {self._token.access_token}"}
