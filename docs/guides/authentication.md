# Authentication

`pysepal-api` uses `httpx.Auth` implementations. Pass one as `auth=...`, or let
the client resolve credentials for you.

## Modes

```python
from pysepal_api import ApiKeyAuth, CookieAuth, NoAuth, SepalClient

# API key (HTTP Basic with the sandbox key as the password)
SepalClient(auth=ApiKeyAuth("my-api-key"))
SepalClient(auth=ApiKeyAuth.from_env("SEPAL_API_KEY"))
SepalClient(auth=ApiKeyAuth.from_sandbox())        # reads the sandbox key file

# Session cookie (Solara container path)
SepalClient(auth=CookieAuth("SEPAL-SESSIONID-value"))
SepalClient(session_id="SEPAL-SESSIONID-value")     # shorthand for CookieAuth

# No auth (e.g. hitting an unauthenticated route)
SepalClient(auth=NoAuth())
```

## Auto-detection

`detect_auth()` picks credentials in order: the `SEPAL_API_KEY` env var, then the
sandbox key file, else it raises `NoCredentialsError`.

```python
from pysepal_api import detect_auth, SepalClient

sepal = SepalClient(auth=detect_auth())
```

If you pass neither `auth` nor `session_id`, the client resolves auth for you
using the same detection logic.
