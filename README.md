# revu-wrangler

A Python SDK for the Bluebeam Cloud API, providing easy access to Bluebeam Studio Sessions and other cloud services. Formerly `bluebeam-py`.

## Features

- **OAuth 2.0 Authentication**: Built-in support for OAuth authorization code flow with automatic token refresh
- **Session Management**: Complete API for managing Bluebeam Studio Sessions
- **Type-Safe**: Fully typed for better IDE support and fewer runtime errors
- **Automatic Retries**: Configurable retry logic with exponential backoff
- **Multi-Region Support**: Support for US, EU, and ANZ regions

## Installation

```bash
uv add revu-wrangler
```

Or with pip:

```bash
pip install revu-wrangler
```

## Quick Start

### 1. Initialize the Client

```python
from revu_wrangler import BluebeamClient

client = BluebeamClient(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="your_redirect_uri",
    region="US"  # Options: "US", "EU", "ANZ"
)
```

### 2. Authenticate

```python
# Get authorization URL
auth_url = client.get_authorization_url(state="optional_state")
print(f"Visit: {auth_url}")

# After user authorizes, exchange code for token
code = "authorization_code_from_redirect"
token = client.set_token_from_code(code)

# Or set token manually if you already have one
client.set_token(
    access_token="your_access_token",
    refresh_token="your_refresh_token",
    expires_in=3600
)
```

### 3. Use the API

```python
# List sessions
sessions = client.sessions.list_sessions()
for session in sessions:
    print(f"Session: {session['Name']} (ID: {session['Id']})")

# Get session details
session = client.sessions.get_session(session_id="session_id")

# Create a new session
new_session = client.sessions.create_session(
    name="My New Session",
    description="Session description"
)
```

## API Reference

### BluebeamClient

The main entry point for the SDK.

**Constructor Parameters:**
- `client_id` (str): Your Bluebeam OAuth client ID
- `client_secret` (str): Your Bluebeam OAuth client secret
- `redirect_uri` (str): OAuth redirect URI
- `region` (str): API region - "US" (default), "EU", or "ANZ"
- `scopes` (List[str], optional): OAuth scopes (defaults to Studio Sessions scopes)
- `timeout` (float): HTTP request timeout in seconds (default: 30.0)
- `max_retries` (int): Maximum number of retry attempts (default: 3)
- `retry_backoff_base` (float): Base for exponential backoff (default: 2.0)

**Methods:**
- `get_authorization_url(state=None)`: Get OAuth authorization URL
- `set_token_from_code(code)`: Exchange authorization code for access token
- `set_token(access_token, refresh_token=None, expires_in=3600)`: Manually set token
- `close()`: Close HTTP client (or use context manager)

**Properties:**
- `sessions`: SessionsAPI instance for session management

### SessionsAPI

Access via `client.sessions`.

**Methods:**
- `list_sessions()`: List all sessions
- `get_session(session_id)`: Get session details
- `create_session(name, description=None, **kwargs)`: Create new session
- `update_session(session_id, **kwargs)`: Update session
- `delete_session(session_id)`: Delete session
- Additional methods for session members, files, and folders

## Exception Handling

```python
from revu_wrangler import (
    BluebeamError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

try:
    sessions = client.sessions.list_sessions()
except AuthenticationError:
    print("Authentication failed - check your credentials")
except NotFoundError:
    print("Resource not found")
except RateLimitError:
    print("Rate limit exceeded - retry later")
except BluebeamError as e:
    print(f"API error: {e}")
```

## Development

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run interactive API smoke check
uv run python development/smoke_sessions.py

# Type checking
uv run mypy .

# Linting
uv run ruff check .
```

## Requirements

- Python >= 3.13
- httpx

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.