from typing import Dict

# Known public regions (extend as needed)
REGION_BASE_URLS: Dict[str, str] = {
    "US": "https://api.bluebeam.com",
    "DE": "https://api.bluebeamstudio.de",
    "AU": "https://api.bluebeamstudio.com.au",
    "UK": "https://api.bluebeamstudio.co.uk",
    "SE": "https://api.bluebeamstudio.se",
}

# Current stable public API root (Session endpoints live under /publicapi/v1/)
API_ROOT = "/publicapi/v1"

# Default scopes for Sessions access; include offline_access to get refresh tokens.
DEFAULT_SCOPES = ["full_user", "offline_access"]

# OAuth paths (relative to region base)
OAUTH_AUTHORIZE_PATH = "/oauth/authorize"
OAUTH_TOKEN_PATH = "/oauth/token"

# Request timeouts (seconds)
DEFAULT_TIMEOUT = 30.0

# Retry defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_BASE = 0.8  # seconds
DEFAULT_RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}
