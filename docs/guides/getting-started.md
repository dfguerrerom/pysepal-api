# Getting started

`pysepal-api` runs inside a SEPAL sandbox (notebook, Voila/Solara app, CLI, or
job) and talks to SEPAL's HTTP services on your behalf.

## Install

```bash
pip install pysepal-api
```

## Construct a client

Construction never performs network I/O. Entering the context (or calling
`create()`) is what eagerly creates the module results directory when you pass
`module_name`.

```python
from pysepal_api import SepalClient

with SepalClient(module_name="my_module") as sepal:
    listing = sepal.files.list("/")
    for entry in listing:
        print(entry.name, entry.type)
```

For a long-lived client, skip the context manager:

```python
sepal = SepalClient.create(module_name="my_module")
try:
    sepal.files.list("/")
finally:
    sepal.close()
```

## Async twin

`AsyncSepalClient` has the identical surface; the only difference is `await`:

```python
from pysepal_api import AsyncSepalClient

async with AsyncSepalClient(module_name="my_module") as sepal:
    listing = await sepal.files.list("/")
```

## Constructor options

`SepalClient(*, session_id=None, module_name=None, auth=None, base_url=None, timeout=30.0, verify=None)`

- `session_id` — SEPAL session cookie (used by the Solara container path).
- `module_name` — creates `module_results/<module_name>` on entry.
- `auth` — an explicit `httpx.Auth` (see [Authentication](authentication.md)).
- `base_url` — override host detection (see [Connecting & TLS](connecting.md)).
- `timeout` — request timeout in seconds (default 30).
- `verify` — TLS verification override.
