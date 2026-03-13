import pytest
import httpx

from revu_wrangler.client import BluebeamClient
from revu_wrangler.config import OAUTH_TOKEN_PATH


def test_client_rejects_unknown_region() -> None:
    with pytest.raises(ValueError):
        BluebeamClient(
            client_id="cid",
            client_secret="secret",
            redirect_uri="https://example.com/callback",
            region="XX",
        )


def test_client_set_token_stores_access_token() -> None:
    client = BluebeamClient(
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://example.com/callback",
        region="US",
    )
    try:
        token = client.set_token(access_token="token-123", refresh_token="refresh-123", expires_in=3600)
        assert token.access_token == "token-123"
        assert client.auth.token is not None
        assert client.auth.token.access_token == "token-123"
    finally:
        client.close()


def test_client_auth_manager_uses_active_http_client() -> None:
    client = BluebeamClient(
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://example.com/callback",
        region="US",
    )
    try:
        assert client.auth._http is client.http
    finally:
        client.close()


def test_auth_hook_allows_oauth_token_request_without_token() -> None:
    client = BluebeamClient(
        client_id="cid",
        client_secret="secret",
        redirect_uri="https://example.com/callback",
        region="US",
    )
    try:
        hook = client.http_event_hooks["request"][0]
        request = httpx.Request("POST", f"{client.base_url}{OAUTH_TOKEN_PATH}")
        hook(request)
    finally:
        client.close()
