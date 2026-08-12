# Authentication

`pysepal-api` uses `httpx.Auth` implementations. Pass one as `auth=...`, or let
the client resolve credentials for you.

## Modes

```python
from pysepal_api import ApiKeyAuth, CookieAuth, NoAuth, SepalClient

# API key (HTTP Basic with the sandbox key as the password)
SepalClient(auth=ApiKeyAuth("my-api-key"))
SepalClient(auth=ApiKeyAuth.from_sandbox())        # reads the sandbox key file

# Session cookie (Solara container path)
SepalClient(auth=CookieAuth("SEPAL-SESSIONID-value"))
SepalClient(session_id="SEPAL-SESSIONID-value")     # shorthand for CookieAuth

# No auth (e.g. hitting an unauthenticated route)
SepalClient(auth=NoAuth())
```

## Resolving credentials for you

If you pass neither `auth` nor `session_id`, the client calls `detect_auth()`,
which reads the sandbox key file at `/var/run/sepal-api-key` and raises
`NoCredentialsError` if it isn't there.

```python
from pysepal_api import detect_auth, SepalClient

sepal = SepalClient()                       # resolves auth for you
sepal = SepalClient(auth=detect_auth())     # the same thing, spelled out
```

`auth_mode=` (and `detect_auth(mode=)`) names what to resolve:

```python
# The sandbox key file. "auto" is the default and means the same thing.
sepal = SepalClient(module_name="my_module", auth_mode="sandbox_file")

# No credentials at all (e.g. hitting an unauthenticated route).
sepal = SepalClient(auth_mode="none")
```

For a Solara app serving several users from one container, don't reach for
`auth_mode` at all — pass each user's own `session_id=` and the client uses
`CookieAuth`.

## Outside a SEPAL sandbox

`/var/run/sepal-api-key` is a sandbox path, so off-sandbox you supply the
credential yourself:

```python
from pysepal_api import ApiKeyAuth, SepalClient, detect_auth

sepal = SepalClient(auth=ApiKeyAuth(my_key))                    # a key you hold
sepal = SepalClient(auth=detect_auth(sandbox_path="/tmp/key"))  # your own file
```
