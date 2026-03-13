from revu_wrangler.config import (
    API_ROOT,
    OAUTH_AUTHORIZE_PATH,
    OAUTH_TOKEN_PATH,
    REGION_BASE_URLS,
)


def test_region_base_urls_have_expected_keys() -> None:
    expected = {"US", "DE", "AU", "UK", "SE"}
    assert expected.issubset(set(REGION_BASE_URLS.keys()))


def test_api_and_oauth_paths_are_stable() -> None:
    assert API_ROOT == "/publicapi/v1"
    assert OAUTH_AUTHORIZE_PATH == "/oauth2/authorize"
    assert OAUTH_TOKEN_PATH == "/oauth2/token"
