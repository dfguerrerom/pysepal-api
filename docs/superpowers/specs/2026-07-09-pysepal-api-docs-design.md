# Design: pysepal-api documentation site (MkDocs Material)

**Date:** 2026-07-09
**Status:** Approved (design), pending implementation plan
**Repo:** `github.com/dfguerrerom/pysepal-api`
**Package:** `pysepal-api` v0.2.0 (MIT)

## Goal

Publish a public documentation site for the `pysepal-api` Python client so that
external SEPAL users and app authors who `pip install pysepal-api` can learn the
library from narrative guides and a complete, auto-generated API reference.

## Subject clarification (important)

`pysepal-api` is an **HTTP client library**, not an HTTP server. It exposes
Python classes/methods (`SepalClient`, `sepal.files.list(...)`), not REST routes.
Therefore:

- The API reference is generated from **docstrings + type hints** via
  **mkdocstrings**, NOT from an OpenAPI spec.
- **OpenAPI / Redoc / Scalar are explicitly out of scope.** Those tools render a
  spec of *server* HTTP routes; they cannot document a Python library. They were
  considered and dropped for this reason. (A separate OpenAPI spec of the SEPAL
  backend endpoints the client wraps could be a future, independent project — it
  is not part of this one.)

## Stack (decided)

| Concern | Choice |
|---|---|
| Framework | MkDocs |
| Theme | Material for MkDocs |
| API reference | `mkdocstrings[python]` (griffe backend) |
| Narrative pages | Markdown |
| Reference layout | Approach A — curated per-group reference pages |
| Hosting | GitHub Pages (via GitHub Actions) |
| Versioned docs | Deferred (single "latest" site for now; `mike` later if wanted) |

## Source facts (verified against the repo)

- Public surface from `src/pysepal_api/__init__.py` `__all__`: clients
  (`SepalClient`, `AsyncSepalClient`), auth (`ApiKeyAuth`, `CookieAuth`, `NoAuth`,
  `detect_auth`), host helpers (`detect_base_url`, `normalize_base_url`), models
  (`Task`, `TaskState`, `FileEntry`, `DirectoryListing`, `FileWriteResult`,
  `RecipeSummary`), and the error hierarchy (`PysepalError` → `ApiError` /
  `ResponseError` / `TransportError` → concrete errors such as `NotFound`,
  `Unauthorized`, `TaskFailed`, …), plus `__version__`.
- Modules under `src/pysepal_api/`: `client`, `auth`, `host`, `models`, `errors`,
  `paths`, `transport`, and `endpoints/{tasks,recipes,user_files,_base}`.
- Docstrings are **plain narrative prose** with embedded code examples — no
  Google/NumPy `Args:`/`Returns:` section headers. Everything is fully type-hinted.
- `requires-python = ">=3.10"`.
- Existing dev tooling: `nox` (`tests`, `lint`, `mypy` sessions), ruff, black,
  mypy, pytest, pre-commit.
- Existing workflows: `.github/workflows/{release.yml,tests.yml}`. No docs workflow.
- `docs/` currently holds only `docs/superpowers/{plans,specs}/` (process docs),
  no MkDocs site yet.

## Site structure

MkDocs `docs_dir` = `docs/`. The existing `docs/superpowers/` tree is excluded
from the built site (see `exclude_docs` below) so process docs never appear on
the public site.

```
docs/
  index.md                 # what it is · install · 30-second sync+async example
  guides/
    getting-started.md     # install, construct a client, first call (sync & async twins)
    authentication.md      # ApiKeyAuth / CookieAuth / NoAuth / detect_auth
    connecting.md          # host detection, base URL, local dev + TLS (insecure hosts)
    usage.md               # tasks (+ wait), recipes, user-files — the common flows
    error-handling.md      # the PysepalError hierarchy; catch/retry patterns
  reference/               # Approach A — one curated page per logical group
    client.md              # ::: pysepal_api.client
    endpoints.md           # ::: pysepal_api.endpoints.tasks / .recipes / .user_files
    models.md              # ::: pysepal_api.models
    auth.md                # ::: pysepal_api.auth
    host.md                # ::: pysepal_api.host
    errors.md              # ::: pysepal_api.errors
  changelog.md             # embeds repo CHANGELOG.md via pymdownx.snippets
```

`transport.py`, `paths.py`, and `endpoints/_base.py` are internal plumbing and
are intentionally **not** given reference pages (kept off the public surface).

Navigation order: Home · Guides (the 5) · API Reference (the 6) · Changelog. The
initial guide set is deliberately lean; pages can be split as content grows.

## `mkdocs.yml` (key configuration)

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
    - scheme: default   # light
      toggle: {icon: material/weather-night, name: Switch to dark mode}
    - scheme: slate      # dark
      toggle: {icon: material/weather-sunny, name: Switch to light mode}

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            filters: ["!^_"]              # hide private members
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
  - pymdownx.snippets            # to embed ../CHANGELOG.md into changelog.md
  - toc:
      permalink: true

exclude_docs: |
  superpowers/

nav:
  - Home: index.md
  - Guides:
      - Getting started: guides/getting-started.md
      - Authentication: guides/authentication.md
      - Connecting & TLS: guides/connecting.md
      - Usage: guides/usage.md
      - Error handling: guides/error-handling.md
  - API Reference:
      - Client: reference/client.md
      - Endpoints: reference/endpoints.md
      - Models: reference/models.md
      - Auth: reference/auth.md
      - Host: reference/host.md
      - Errors: reference/errors.md
  - Changelog: changelog.md
```

Notes:
- `mkdocstrings` reads packages from `src/` via `paths: [src]`. Installing the
  package editable (`pip install -e .[docs]`, as the nox session and CI both do)
  additionally ensures imports resolve cleanly for griffe.
- Docstring style is left at the handler default (griffe). Because the docstrings
  contain no section headers, prose renders verbatim — no `docstring_style` needed.

## Dependencies & nox

Add a `docs` group to `[project.optional-dependencies]` in `pyproject.toml`,
alongside the existing `dev` group:

```toml
docs = [
  "mkdocs>=1.6",
  "mkdocs-material>=9.5",
  "mkdocstrings[python]>=0.26",
  "griffe>=1.0",
]
```

Add two `noxfile.py` sessions mirroring the existing pattern:

```python
@nox.session(reuse_venv=True)
def docs(session):
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build", "--strict")

@nox.session(reuse_venv=True)
def docs_serve(session):
    session.install("-e", ".[docs]")
    session.run("mkdocs", "serve", *session.posargs)
```

## Build & deploy (GitHub Pages)

New workflow `.github/workflows/docs.yml`:

- Trigger: push to `main` (and manual `workflow_dispatch`).
- Steps: checkout → setup Python 3.12 → `pip install -e .[docs]` →
  `mkdocs build --strict` → `actions/upload-pages-artifact` (path `site/`) →
  `actions/deploy-pages`.
- Permissions: `pages: write`, `id-token: write`; `concurrency` group `pages`.

**Manual one-time step (owner):** repo **Settings → Pages → Source: "GitHub
Actions"**. This cannot be done from code and must be enabled once before the
first deploy succeeds. Resulting URL: `https://dfguerrerom.github.io/pysepal-api/`.

`mike` (versioned docs with a version selector) is deferred; the site serves a
single "latest" build. Revisit if/when multiple supported versions matter.

## Repo housekeeping

- Add `[project.urls]` to `pyproject.toml`:
  `Homepage`, `Repository`, `Documentation`
  (`https://dfguerrerom.github.io/pysepal-api/`), `Changelog`.
- Add a documentation link (and optional badge) to `README.md`.
- Add `site/` to `.gitignore` (MkDocs build output).

## Testing / verification (the gate)

- `mkdocs build --strict` must complete with **no warnings** (broken nav,
  unresolved cross-references, or missing pages fail the build). This is wired
  into both the `docs` nox session and CI.
- Local preview: `nox -s docs_serve` → http://127.0.0.1:8000.
- Reference pages must render every public (`__all__`) symbol; private members
  (leading underscore) must be absent.

## Out of scope

- OpenAPI spec, Redoc, Scalar (see Subject clarification).
- Versioned docs / `mike`.
- Documenting the full SEPAL backend REST API.
- Reference pages for internal modules (`transport`, `paths`, `endpoints._base`).
- Custom domain for Pages.

## Open items (require owner action, not code)

1. Enable GitHub Pages "Source: GitHub Actions" in repo settings (one-time).
```
