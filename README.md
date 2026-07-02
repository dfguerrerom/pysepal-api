# pysepal-api

UI-free HTTP client for SEPAL platform services. Powers Jupyter notebooks, Voila apps, CLI scripts, and background jobs running inside a SEPAL sandbox.

```python
from pysepal_api import SepalClient

# sync — notebooks, CLI, jobs
with SepalClient.create(session_id="...") as sepal:
    listing = sepal.user_files.list("/")
    task = sepal.tasks.submit("image.download", params={...})
    sepal.tasks.wait(task.id)

    # escape hatch: any route the typed endpoints don't model
    image = sepal.get("/api/gee/image/json", params={"recipeId": "foo"}).json()
```

```python
from pysepal_api import AsyncSepalClient

# async — Voila / Solara
async with await AsyncSepalClient.create(session_id="...") as sepal:
    listing = await sepal.user_files.list("/")
    image = (await sepal.get("/api/gee/image/json", params={"recipeId": "foo"})).json()
```

The two clients are twins: identical surface, the only difference is `await`.

- **Construct with `create()`** (or a `with` / `async with` block). `SepalClient(...)` works too, but never performs network I/O until you enter the context — `create()`/entry is what creates the module results dir.
- **Typed endpoints** for the common cases: `user_files`, `tasks`, `recipes`.
- **Generic primitive** — `request()` / `get()` / `post()` / `put()` / `delete()` — for any other SEPAL route, with the same typed-error mapping (`NotFound`, `Unauthorized`, …). Returns the raw `httpx.Response`.
- **One exception root** — catch `PysepalError` for anything this library raises.

TLS is verified by default. `host.docker.internal` is auto-skipped for local dev; for any other self-signed host set `PYSEPAL_INSECURE_TLS=1` or pass `verify=False`.

See `docs/` for the design spec.
