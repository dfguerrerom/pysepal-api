# pysepal-api

UI-free HTTP client for SEPAL platform services. Powers Jupyter notebooks, Voila/Solara apps, CLI scripts, and background jobs running inside a SEPAL sandbox.

## Install

```bash
pip install pysepal-api
```

## 30-second example

```python
from pysepal_api import SepalClient

# sync — notebooks, CLI, jobs
with SepalClient(module_name="my_module") as sepal:
    listing = sepal.files.list("/")
    task = sepal.tasks.submit("image.download", params={})
    sepal.tasks.wait(task.id)
```

```python
from pysepal_api import AsyncSepalClient

# async — Voila / Solara
async with AsyncSepalClient(module_name="my_module") as sepal:
    listing = await sepal.files.list("/")
```

The two clients are twins: identical surface, the only difference is `await`.

## Where to go next

- **[Getting started](guides/getting-started.md)** — install, construct a client, first call
- **[Authentication](guides/authentication.md)** — API key, session cookie, auto-detect
- **[Connecting & TLS](guides/connecting.md)** — host resolution and local-dev TLS
- **[Usage](guides/usage.md)** — files, tasks, recipes
- **[Error handling](guides/error-handling.md)** — the exception hierarchy
- **[API Reference](reference/client.md)** — full generated reference
