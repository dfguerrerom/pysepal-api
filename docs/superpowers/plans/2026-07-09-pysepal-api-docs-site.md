# pysepal-api Documentation Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a public MkDocs Material documentation site for the `pysepal-api` Python client, with narrative guides and an auto-generated API reference, deployable to GitHub Pages.

**Architecture:** MkDocs + Material theme renders Markdown guides; `mkdocstrings[python]` generates the API reference from the package's docstrings and type hints (Approach A: one curated reference page per logical group). The build gate is `mkdocs build --strict` (broken nav/refs fail the build). A GitHub Actions workflow builds and deploys to Pages.

**Tech Stack:** MkDocs ≥1.6, mkdocs-material ≥9.5, mkdocstrings[python] ≥0.26, griffe ≥1.0, nox, GitHub Actions (Pages).

## Global Constraints

- Package name: `pysepal-api`; import package: `pysepal_api`; version 0.2.0; license MIT.
- `requires-python = ">=3.10"`.
- Repo: `github.com/dfguerrerom/pysepal-api`; Pages URL `https://dfguerrerom.github.io/pysepal-api/`.
- Source layout is `src/` (mkdocstrings must read via `paths: [src]`).
- `mkdocs build --strict` MUST pass with zero warnings at the end of every task that touches docs.
- Docstrings are plain prose (no `Args:`/`Returns:` sections) and fully type-hinted — do NOT set a `docstring_style`; leave the griffe default.
- Reference pages are generated ONLY for public modules: `client`, `endpoints.{tasks,recipes,user_files}`, `models`, `auth`, `host`, `errors`. Never document internal modules `transport`, `paths`, `endpoints._base`, or any `_`-prefixed member (enforced by `filters: ["!^_"]`).
- Commit messages: concise, imperative, NO `Co-Authored-By` / Claude authorship lines. Repo uses commitizen (conventional commits) in pre-commit — subjects MUST follow `type: subject` (e.g. `docs:`, `build:`, `ci:`, `chore:`).
- Do NOT push. All commits are local; the user pushes.

## File Structure

Created:
- `mkdocs.yml` — site config, theme, plugins, nav (repo root)
- `docs/index.md` — landing page
- `docs/guides/{getting-started,authentication,connecting,usage,error-handling}.md`
- `docs/reference/{client,endpoints,models,auth,host,errors}.md`
- `docs/changelog.md` — embeds `CHANGELOG.md`
- `.github/workflows/docs.yml` — Pages build+deploy

Modified:
- `pyproject.toml` — add `docs` optional-dependency group + `[project.urls]`
- `noxfile.py` — add `docs` + `docs_serve` sessions
- `.gitignore` — add `site/`
- `README.md` — add documentation link

Untouched by the site build: `docs/superpowers/**` (excluded via `exclude_docs`).

---

### Task 1: Scaffold — deps, config, landing page, nox, buildable Home-only site

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/index.md`
- Modify: `pyproject.toml` (add `docs` extra + `[project.urls]`)
- Modify: `noxfile.py` (add `docs`, `docs_serve` sessions)
- Modify: `.gitignore` (add `site/`)

**Interfaces:**
- Produces: a working MkDocs project whose `nav` initially contains only `Home: index.md`. Later tasks append `Guides`, `API Reference`, and `Changelog` nav sections and their pages. The `mkdocstrings` plugin and all `markdown_extensions` are configured here so later tasks only add pages.

- [ ] **Step 1: Add the `docs` extra and `[project.urls]` to `pyproject.toml`**

In `[project.optional-dependencies]`, add a `docs` group next to the existing `dev` group:

```toml
docs = [
  "mkdocs>=1.6",
  "mkdocs-material>=9.5",
  "mkdocstrings[python]>=0.26",
  "griffe>=1.0",
]
```

Add a new `[project.urls]` table (place it right after the `[project]` table, before `[project.optional-dependencies]`):

```toml
[project.urls]
Homepage = "https://dfguerrerom.github.io/pysepal-api/"
Documentation = "https://dfguerrerom.github.io/pysepal-api/"
Repository = "https://github.com/dfguerrerom/pysepal-api"
Changelog = "https://github.com/dfguerrerom/pysepal-api/blob/main/CHANGELOG.md"
```

- [ ] **Step 2: Create `mkdocs.yml`** (repo root) with the full config. Nav has ONLY Home for now:

```yaml
site_name: pysepal-api
site_description: UI-free HTTP client for SEPAL platform services (user files, tasks, recipes).
site_url: https://dfguerrerom.github.io/pysepal-api/
repo_url: https://github.com/dfguerrerom/pysepal-api
repo_name: dfguerrerom/pysepal-api

theme:
  name: material
  features:
    - navigation.sections
    - navigation.top
    - content.code.copy
    - toc.follow
    - search.suggest
  palette:
    - scheme: default
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - scheme: slate
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            filters: ["!^_"]
            show_root_heading: true
            show_source: true
            separate_signature: true
            show_signature_annotations: true
            members_order: source
            merge_init_into_class: true

markdown_extensions:
  - admonition
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.snippets:
      base_path: ["."]
      check_paths: true
  - toc:
      permalink: true

exclude_docs: |
  superpowers/

nav:
  - Home: index.md
```

- [ ] **Step 3: Create `docs/index.md`** (landing page — reuses the canonical README examples):

````markdown
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
````

Note: the `guides/*` and `reference/*` links above intentionally point to pages created in Tasks 2–3. They are Markdown links, not nav entries, so `--strict` will warn about them until those files exist. To keep Task 1 building clean, temporarily omit the "Where to go next" list, OR create the target files as one-line stubs now and fill them in later. **Chosen approach:** omit "Where to go next" in Task 1; re-add it in Task 3 Step (final) once all targets exist. Create `docs/index.md` WITHOUT the "Where to go next" section for this task.

- [ ] **Step 4: Add nox sessions to `noxfile.py`** (append after the existing `mypy` session):

```python
@nox.session(reuse_venv=True)
def docs(session: nox.Session) -> None:
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build", "--strict")


@nox.session(reuse_venv=True)
def docs_serve(session: nox.Session) -> None:
    session.install("-e", ".[docs]")
    session.run("mkdocs", "serve", *session.posargs)
```

- [ ] **Step 5: Add `site/` to `.gitignore`**

Append this line to `.gitignore`:

```
site/
```

- [ ] **Step 6: Install docs deps into the working env** (fast inner-loop for later steps)

Run: `pip install -e '.[docs]'`
Expected: installs mkdocs, mkdocs-material, mkdocstrings, griffe without error.

- [ ] **Step 7: Build and verify strict pass**

Run: `mkdocs build --strict`
Expected: `INFO - Documentation built in ...`, exit code 0, NO `WARNING` lines. The `docs/superpowers/` tree must NOT appear in output (excluded).

- [ ] **Step 8: Verify the canonical nox session too**

Run: `nox -s docs`
Expected: session creates a venv, installs `.[docs]`, runs `mkdocs build --strict`, exits 0.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml mkdocs.yml docs/index.md noxfile.py .gitignore
git commit -m "build: scaffold MkDocs Material docs site"
```

---

### Task 2: API reference pages (Approach A)

**Files:**
- Create: `docs/reference/client.md`
- Create: `docs/reference/endpoints.md`
- Create: `docs/reference/models.md`
- Create: `docs/reference/auth.md`
- Create: `docs/reference/host.md`
- Create: `docs/reference/errors.md`
- Modify: `mkdocs.yml` (append the `API Reference` nav section)

**Interfaces:**
- Consumes: the `mkdocstrings` python handler configured in Task 1.
- Produces: six reference pages. The `::: <identifier>` blocks below are mkdocstrings autodoc directives; each renders the named object's signature + docstring.

- [ ] **Step 1: Create `docs/reference/client.md`**

```markdown
# Client

The two clients are twins — identical surface, the only difference is `await`.

## SepalClient

::: pysepal_api.SepalClient

## AsyncSepalClient

::: pysepal_api.AsyncSepalClient
```

- [ ] **Step 2: Create `docs/reference/endpoints.md`**

```markdown
# Endpoints

Accessed as `sepal.files`, `sepal.tasks`, and `sepal.recipes`. Each sync class
below has an identical async twin (`AsyncUserFilesEndpoint`, `AsyncTasksEndpoint`,
`AsyncRecipesEndpoint`) whose methods mirror these with `await`.

## Files — `sepal.files`

::: pysepal_api.endpoints.user_files.UserFilesEndpoint

## Tasks — `sepal.tasks`

::: pysepal_api.endpoints.tasks.TasksEndpoint

## Recipes — `sepal.recipes`

::: pysepal_api.endpoints.recipes.RecipesEndpoint
```

- [ ] **Step 3: Create `docs/reference/models.md`**

```markdown
# Models

Pydantic v2 models returned by the endpoints. Attributes are `snake_case`;
extra server fields are ignored so payload additions never break clients.

::: pysepal_api.models
```

- [ ] **Step 4: Create `docs/reference/auth.md`**

```markdown
# Authentication

::: pysepal_api.auth
```

- [ ] **Step 5: Create `docs/reference/host.md`**

```markdown
# Host resolution

::: pysepal_api.host
```

- [ ] **Step 6: Create `docs/reference/errors.md`**

```markdown
# Errors

Every exception this library raises descends from `PysepalError`, so a single
`except PysepalError` catches them all.

::: pysepal_api.errors
```

- [ ] **Step 7: Append the API Reference nav section to `mkdocs.yml`**

Under `nav:` (after the `Home` entry) add:

```yaml
  - API Reference:
      - Client: reference/client.md
      - Endpoints: reference/endpoints.md
      - Models: reference/models.md
      - Auth: reference/auth.md
      - Host: reference/host.md
      - Errors: reference/errors.md
```

- [ ] **Step 8: Build strict**

Run: `mkdocs build --strict`
Expected: exit 0, no warnings. (mkdocstrings resolving a bad path or missing object surfaces as a warning → strict failure.)

- [ ] **Step 9: Verify autodoc actually rendered the public symbols**

Run: `grep -rl "SepalClient" site/reference/ && grep -rl "TaskState" site/reference/ && grep -rl "PysepalError" site/reference/`
Expected: matches in `site/reference/client/index.html`, `.../models/index.html`, `.../errors/index.html`.

Run: `grep -rn "_resolve_config\|class _Base\|_SyncEndpoint" site/reference/ || echo "no private members (correct)"`
Expected: `no private members (correct)` — the `filters` hid them.

- [ ] **Step 10: Commit**

```bash
git add docs/reference/ mkdocs.yml
git commit -m "docs: add generated API reference pages"
```

---

### Task 3: Narrative guides

**Files:**
- Create: `docs/guides/getting-started.md`
- Create: `docs/guides/authentication.md`
- Create: `docs/guides/connecting.md`
- Create: `docs/guides/usage.md`
- Create: `docs/guides/error-handling.md`
- Modify: `mkdocs.yml` (append the `Guides` nav section)
- Modify: `docs/index.md` (re-add the "Where to go next" links now that targets exist)

**Interfaces:**
- Consumes: nothing from prior tasks beyond the built site. All code samples use the real public API (verified signatures below).

- [ ] **Step 1: Create `docs/guides/getting-started.md`**

````markdown
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
````

- [ ] **Step 2: Create `docs/guides/authentication.md`**

````markdown
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
````

- [ ] **Step 3: Create `docs/guides/connecting.md`**

````markdown
# Connecting & TLS

## Host resolution

If you don't pass `base_url`, the client detects the SEPAL host from the sandbox
environment. You can inspect or override it:

```python
from pysepal_api import detect_base_url, normalize_base_url, SepalClient

print(detect_base_url())                 # e.g. https://sepal.io
SepalClient(base_url="https://sepal.io")
SepalClient(base_url=normalize_base_url("sepal.io"))  # adds scheme, strips trailing slash
```

## TLS verification

TLS is **verified by default**. Two escape hatches exist for local development
with self-signed certificates:

- `host.docker.internal` is auto-trusted (skipped) for local dev.
- Any other self-signed host: pass `verify=False`, or list it in the
  `PYSEPAL_INSECURE_TLS_HOSTS` env var (comma-separated, exact-host match).

```python
# local dev against a self-signed host
SepalClient(base_url="https://my-dev-host", verify=False)
```

```bash
export PYSEPAL_INSECURE_TLS_HOSTS="my-dev-host,another-host"
```

Verification is never skipped for arbitrary or production hosts.
````

- [ ] **Step 4: Create `docs/guides/usage.md`**

````markdown
# Usage

All examples use the sync client; the async twin mirrors them with `await`.

## Files — `sepal.files`

File verbs follow `pathlib`:

```python
listing = sepal.files.list("/", extensions=[".tif"], include_hidden=False)
print(listing.count, len(listing))
for entry in listing:                 # DirectoryListing iterates its entries
    print(entry.name, entry.is_dir)

data = sepal.files.read_json("results/summary.json")
text = sepal.files.read_text("notes.txt")
raw = sepal.files.read_bytes("image.tif")

result = sepal.files.write("out/report.txt", "hello", overwrite=True)
sepal.files.mkdir("out/nested")       # idempotent
module_path = sepal.files.module_dir("my_module")
```

## Tasks — `sepal.tasks`

```python
task = sepal.tasks.submit("image.download", params={"recipeId": "abc"})
final = sepal.tasks.wait(task.id, poll_interval=5.0, timeout=600)
print(final.state)                    # a TaskState enum member

running = sepal.tasks.list(status="ACTIVE")
sepal.tasks.cancel(task.id)
sepal.tasks.restart(task.id)          # maps to SEPAL's execute route
sepal.tasks.remove(task.id)
```

## Recipes — `sepal.recipes`

```python
summaries = sepal.recipes.list()      # list[RecipeSummary]
recipe = sepal.recipes.get("recipe-id")          # parsed JSON
raw = sepal.recipes.get_raw("recipe-id")         # exact stored bytes

sepal.recipes.save(
    "recipe-id",
    project_id="proj-1",
    type="CLASSIFICATION",
    name="My recipe",
    contents={"key": "value"},        # JSON-serializable or bytes/str
)
sepal.recipes.delete("recipe-id")
```

## Escape hatch — any other route

The typed endpoints cover the common cases; for anything else use the generic
primitives. They return the raw `httpx.Response` with the same typed-error
mapping.

```python
image = sepal.get("/api/gee/image/json", params={"recipeId": "foo"}).json()
sepal.post("/api/some/route", json={"a": 1})
```
````

- [ ] **Step 5: Create `docs/guides/error-handling.md`**

````markdown
# Error handling

Every exception this library raises descends from `PysepalError`, so one
`except PysepalError` is enough to catch anything it throws.

```
PysepalError
├── ApiError                (HTTP status → typed)
│   ├── BadRequest          (400)
│   ├── Unauthorized        (401)
│   ├── Forbidden           (403)
│   ├── NotFound            (404)
│   ├── Conflict            (409)
│   ├── TooManyRequests     (429)
│   └── ServerError         (5xx)
├── TransportError          (connection / timeout at the socket level)
├── ResponseError          (unexpected/unparseable response body)
├── NoCredentialsError     (no auth could be resolved)
├── MissingHostError       (no base URL could be resolved)
├── InvalidPathError       (also a ValueError)
└── TaskError
    ├── TaskFailed          (task reached FAILED)
    ├── TaskCanceled        (task reached CANCELED)
    └── TaskTimeout         (also a TimeoutError; wait() exceeded its timeout)
```

## Catch specific cases

```python
from pysepal_api import Conflict, NotFound, PysepalError, TaskFailed, TaskTimeout

try:
    sepal.files.write("out/report.txt", "hi")     # may raise Conflict if it exists
except Conflict:
    sepal.files.write("out/report.txt", "hi", overwrite=True)

try:
    final = sepal.tasks.wait(task.id, timeout=600)
except TaskTimeout:
    ...        # still running after 600s
except TaskFailed as exc:
    print(exc.task.state)                          # the terminal Task is attached

try:
    sepal.files.read_json("missing.json")
except NotFound:
    ...
except PysepalError as exc:
    ...        # anything else from the library
```
````

- [ ] **Step 6: Append the Guides nav section to `mkdocs.yml`**

Insert this block under `nav:`, BETWEEN `Home` and `API Reference`:

```yaml
  - Guides:
      - Getting started: guides/getting-started.md
      - Authentication: guides/authentication.md
      - Connecting & TLS: guides/connecting.md
      - Usage: guides/usage.md
      - Error handling: guides/error-handling.md
```

- [ ] **Step 7: Re-add the "Where to go next" section to `docs/index.md`**

Append to `docs/index.md` (all targets now exist, so `--strict` stays clean):

```markdown
## Where to go next

- **[Getting started](guides/getting-started.md)** — install, construct a client, first call
- **[Authentication](guides/authentication.md)** — API key, session cookie, auto-detect
- **[Connecting & TLS](guides/connecting.md)** — host resolution and local-dev TLS
- **[Usage](guides/usage.md)** — files, tasks, recipes
- **[Error handling](guides/error-handling.md)** — the exception hierarchy
- **[API Reference](reference/client.md)** — full generated reference
```

- [ ] **Step 8: Build strict**

Run: `mkdocs build --strict`
Expected: exit 0, no warnings (all internal links and nav entries resolve).

- [ ] **Step 9: Commit**

```bash
git add docs/guides/ docs/index.md mkdocs.yml
git commit -m "docs: add getting-started, auth, connecting, usage, error guides"
```

---

### Task 4: Changelog page + README link

**Files:**
- Create: `docs/changelog.md`
- Modify: `mkdocs.yml` (append `Changelog` nav entry)
- Modify: `README.md` (add documentation link)

**Interfaces:**
- Consumes: `pymdownx.snippets` (configured in Task 1 with `base_path: ["."]`, so paths resolve from the repo root where `mkdocs` runs).

- [ ] **Step 1: Create `docs/changelog.md`** embedding the repo changelog:

```markdown
# Changelog

--8<-- "CHANGELOG.md"
```

- [ ] **Step 2: Append the Changelog nav entry to `mkdocs.yml`**

Add as the LAST entry under `nav:`:

```yaml
  - Changelog: changelog.md
```

- [ ] **Step 3: Add a documentation link to `README.md`**

Insert directly under the top-level `# pysepal-api` title line:

```markdown
📖 **[Documentation](https://dfguerrerom.github.io/pysepal-api/)**
```

- [ ] **Step 4: Build strict**

Run: `mkdocs build --strict`
Expected: exit 0, no warnings.

- [ ] **Step 5: Verify the changelog embedded**

Run: `grep -rl "Changelog" site/changelog/index.html && grep -c "h2\|h3" site/changelog/index.html`
Expected: the file matches, and the embedded CHANGELOG headings are present (non-zero count).

- [ ] **Step 6: Commit**

```bash
git add docs/changelog.md mkdocs.yml README.md
git commit -m "docs: add changelog page and README docs link"
```

---

### Task 5: GitHub Pages deploy workflow

**Files:**
- Create: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: the `docs` extra (`pip install -e .[docs]`) and `mkdocs build --strict`.
- Produces: a CI workflow that builds `site/` and deploys it to GitHub Pages on push to `main`.

- [ ] **Step 1: Create `.github/workflows/docs.yml`**

```yaml
name: docs

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[docs]"
      - run: mkdocs build --strict
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate the workflow YAML locally**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/docs.yml')); print('valid yaml')"`
Expected: `valid yaml`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: build and deploy docs to GitHub Pages"
```

- [ ] **Step 4: Owner action (manual, not code) — record in the handoff**

The repo owner must enable **Settings → Pages → Source: "GitHub Actions"** once,
before the first deploy can publish. This cannot be scripted. After it's enabled
and the workflow runs on `main`, the site is live at
`https://dfguerrerom.github.io/pysepal-api/`.

---

## Definition of Done

- `mkdocs build --strict` and `nox -s docs` pass with zero warnings.
- `nox -s docs_serve` renders Home, all 5 guides, all 6 reference pages, and the changelog.
- API reference shows every public (`__all__`) symbol; no `_`-prefixed members appear.
- `.github/workflows/docs.yml` is present and valid.
- All work committed locally (not pushed). One outstanding owner action: enable Pages "Source: GitHub Actions".
