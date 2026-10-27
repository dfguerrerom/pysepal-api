# pysepal-api

📖 **[Documentation](https://dfguerrerom.github.io/pysepal-api/)**

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
- **Typed endpoints** for the common cases: `files`, `tasks`, `recipes`, `ee_exports`. File verbs follow `pathlib`: `read_bytes` / `read_text` / `read_json` / `write` / `mkdir`.
- **Generic primitive** — `request()` / `get()` / `post()` / `put()` / `delete()` — for any other SEPAL route, with the same typed-error mapping (`NotFound`, `Unauthorized`, …). Returns the raw `httpx.Response`.
- **One exception root** — catch `PysepalError` for anything this library raises.

TLS is verified by default. `host.docker.internal` is auto-skipped for local dev; for any other self-signed host pass `verify=False` or list it in `PYSEPAL_INSECURE_TLS_HOSTS` (comma-separated, exact-host match).

## Earth Engine exports

`sepal.ee_exports` (alias `sepal.exports`) routes notebook-created `ee.Image` and `ee.FeatureCollection` exports through SEPAL's TaskManager. It serializes the EE object into a Cloud API expression and submits an `ee.export` task — no new HTTP route, so `tasks.wait(task.id)` tracks it like any other task.

Requires the SEPAL backend adapter in [openforis/sepal#454](https://github.com/openforis/sepal/pull/454). See [the export notebook](examples/ee_exports.ipynb) for a runnable sandbox example.

Serializing a live EE object needs the optional Earth Engine extra:

```bash
pip install "pysepal-api[ee]"
```

`submit_image(...)` and `submit_table(...)` each take a `destination` of `"SEPAL"`, `"DRIVE"`, or `"GEE"`:

```python
import ee
from pysepal_api import SepalClient

ee.Initialize()
image = ee.Image("COPERNICUS/S2_SR/...").normalizedDifference(["B8", "B4"])
region = ee.Geometry.Rectangle([0, 0, 1, 1])

with SepalClient(session_id="...", module_name="my_module") as sepal:
    # → SEPAL sandbox. workspace_path is RELATIVE to your SEPAL home dir.
    task = sepal.ee_exports.submit_image(
        image=image, region=region, destination="SEPAL",
        name="ndvi_2026", scale=30,
        workspace_path="module_results/my_module/exports",
    )

    # → Google Drive
    sepal.ee_exports.submit_image(
        image=image, region=region, destination="DRIVE",
        name="ndvi_2026", scale=30, drive_folder="SEPAL/exports",
    )

    # → Earth Engine asset (asset_id is required for GEE)
    sepal.ee_exports.submit_image(
        image=image, region=region, destination="GEE",
        name="ndvi_2026", scale=30,
        asset_id="projects/my-project/assets/exports/ndvi_2026",
    )

    # FeatureCollection → asset
    sepal.ee_exports.submit_table(
        collection=ee.FeatureCollection("..."), destination="GEE",
        name="plots", asset_id="projects/my-project/assets/exports/plots",
    )

    sepal.tasks.wait(task.id)
```

Notes:

- `workspace_path` is **relative to your SEPAL home directory** — never pass an absolute path (the worker rejects `..` traversal).
- `destination="GEE"` requires `asset_id`; omitting it raises `ValueError` before any network call.
- `image` / `collection` / `region` accept either a live EE object (encoded for you) or an already-encoded Cloud API expression dict (no `[ee]` extra needed).
- Table `max_vertices` is supported by the current backend only for Drive exports. ImageCollection asset exports require SEPAL's tiled recipe workflow.
- SEPAL's task list shows where each export came from: the notebook or script path (relative to your home directory), or the app. Apps name themselves with `SepalClient(..., app_name="se.plan")`; without it, a client signed in with `session_id` is named after its `module_name`. Code with no notebook or script (a Python shell, `python -c`, Voila) shows its working directory.
- The async twin `AsyncSepalClient.ee_exports` has the identical surface, differing only by `await`.
