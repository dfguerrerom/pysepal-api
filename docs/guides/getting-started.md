# Getting started

`pysepal-api` runs inside a SEPAL sandbox (notebook, Voila/Solara app, CLI, or
job) and talks to SEPAL's HTTP services on your behalf.

## Install

```bash
pip install pysepal-api
```

## Construct a client

Construction and `create()` are pure, so building a client is safe anywhere —
including a UI render path.

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

## The results directory

`module_name` gives the client a `results_path` of
`/home/sepal-user/module_results/<module_name>`, derived arithmetically.
`ensure_results_dir()` is what creates that directory on the server, so call it
before anything writes there — a write into a missing directory fails at write
time, with nothing to warn you at construction.

Make the call once, during app startup, and keep it off render paths: it
performs network I/O and re-issues the request every time rather than caching
that the directory is already there.

```python
sepal = SepalClient.create(module_name="my_module")
sepal.ensure_results_dir()      # once, at startup

# ...later, on a save path — the directory is already there
sepal.files.write("module_results/my_module/report.csv", payload)
```

The async twin is `await sepal.ensure_results_dir()`. Either returns the
absolute `results_path`, or `None` when the client has no `module_name`.

## Constructor options

`SepalClient(*, session_id=None, module_name=None, auth=None, auth_mode="auto", base_url=None, timeout=30.0, verify=None)`

- `session_id` — SEPAL session cookie (used by the Solara container path).
- `module_name` — derives `results_path` as `module_results/<module_name>`; call `ensure_results_dir()` to create it.
- `auth` — an explicit `httpx.Auth` (see [Authentication](authentication.md)).
- `auth_mode` — `"sandbox_file"` (what the default `"auto"` resolves to) or `"none"` (see [Authentication](authentication.md)). Ignored when `auth` or `session_id` is passed.
- `base_url` — override host detection (see [Connecting & TLS](connecting.md)).
- `timeout` — request timeout in seconds (default 30).
- `verify` — TLS verification override.
