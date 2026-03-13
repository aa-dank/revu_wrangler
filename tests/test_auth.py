import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from revu_wrangler.auth import AuthManager, OAuthToken
from revu_wrangler.exceptions import AuthenticationError


BASE_URL = "https://api.bluebeam.com"


def _make_auth(http: httpx.Client | None = None) -> AuthManager:
    return AuthManager(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://example.com/callback",
        scopes=["full_user", "offline_access"],
        http=http,
    )


def test_authorization_url_contains_expected_params() -> None:
    auth = _make_auth()
    url = auth.authorization_url(state="xyz")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "api.bluebeam.com"
    assert parsed.path == "/oauth2/authorize"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["cid"]
    assert query["redirect_uri"] == ["https://example.com/callback"]
    assert query["state"] == ["xyz"]
    assert query["scope"] == ["full_user offline_access"]


def test_exchange_code_for_token_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/oauth2/token"
        return httpx.Response(
            status_code=200,
            json={
                "access_token": "a1",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "r1",
                "scope": "full_user offline_access",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    auth = _make_auth(http=client)

    tok = auth.exchange_code_for_token("abc")
    assert tok.access_token == "a1"
    assert tok.refresh_token == "r1"


def test_exchange_code_for_token_failure_raises_authentication_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=401, text="bad code")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    auth = _make_auth(http=client)

    with pytest.raises(AuthenticationError):
        auth.exchange_code_for_token("bad")


def test_get_auth_header_refreshes_expired_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "access_token": "new-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "refresh-token",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    auth = _make_auth(http=client)

    expired = OAuthToken(
        access_token="old-token",
        token_type="Bearer",
        expires_in=60,
        refresh_token="refresh-token",
        obtained_at=time.time() - 600,
    )
    auth.set_token(expired)

    header = auth.get_auth_header()
    assert header["Authorization"] == "Bearer new-token"


def test_get_auth_header_without_token_raises_authentication_error() -> None:
    auth = _make_auth()
    with pytest.raises(AuthenticationError):
        auth.get_auth_header()
