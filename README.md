# pysepal-api

UI-free HTTP client for SEPAL platform services. Powers Jupyter notebooks, Voila apps, CLI scripts, and background jobs running inside a SEPAL sandbox.

```python
from pysepal_api import SepalClient

# sync — notebooks, CLI, jobs
with SepalClient(session_id="...") as sepal:
    listing = sepal.files.list("/")
    task = sepal.tasks.submit("image.download", params={...})
    sepal.tasks.wait(task.id)

    # escape hatch: any route the typed endpoints don't model
    image = sepal.get("/api/gee/image/json", params={"recipeId": "foo"}).json()
```

```python
from pysepal_api import AsyncSepalClient

# async — Voila / Solara
async with AsyncSepalClient(session_id="...") as sepal:
    listing = await sepal.files.list("/")
    image = (await sepal.get("/api/gee/image/json", params={"recipeId": "foo"})).json()
```

The two clients are twins: identical surface, the only difference is `await`.

- **Scoped use** — `with SepalClient(...)` / `async with AsyncSepalClient(...)`. Construction never performs network I/O; entering the context creates the module results dir (when `module_name` is given).
- **Long-lived clients** — `sepal = SepalClient.create(...)` / `sepal = await AsyncSepalClient.create(...)`: same eager setup without a context manager; call `close()` / `aclose()` when done. `async with AsyncSepalClient.create(...)` also works.
- **Typed endpoints** for the common cases: `files`, `tasks`, `recipes`. File verbs follow `pathlib`: `read_bytes` / `read_text` / `read_json` / `write` / `mkdir`.
- **Generic primitive** — `request()` / `get()` / `post()` / `put()` / `delete()` — for any other SEPAL route, with the same typed-error mapping (`NotFound`, `Unauthorized`, …). Returns the raw `httpx.Response`.
- **One exception root** — catch `PysepalError` for anything this library raises.

TLS is verified by default. `host.docker.internal` is auto-skipped for local dev; for any other self-signed host pass `verify=False` or list it in `PYSEPAL_INSECURE_TLS_HOSTS` (comma-separated, exact-host match).
