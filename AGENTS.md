# AGENTS.md — pysepal-api

Agent-facing notes. Keep terse; this file is loaded into every Codex session for this repo.

## What this project is

UI-free HTTP client library for SEPAL platform services. **Library, not an app** — no Dockerfile, no runtime image, no lockfile. Powers notebooks, Voila apps, CLI scripts, background jobs. Companion to `pysepal` (Solara UI components) — do not add UI dependencies here.

- Package: `pysepal-api` (PyPI name) → `pysepal_api` (import name)
- Repo: `github.com/dfguerrerom/pysepal-api` (private as of 2026-05-16)
- Python: 3.10 – 3.12
- Build: `hatchling`. Version in `pyproject.toml [project].version` AND `src/pysepal_api/__init__.py:__version__` — both must stay in sync (commitizen handles this).

## Architecture in one paragraph

`httpx`-based with sync `SepalClient` and `AsyncSepalClient` parity. Construct with `with SepalClient(...)` / `async with AsyncSepalClient(...)` for scoped use, or the `create()` factory for long-lived clients — `AsyncSepalClient.create()` returns an awaitable that is *also* an async context manager. `__init__` does **no** network I/O. Client endpoint attributes are `files`, `tasks`, `recipes` (modules `endpoints/user_files.py`, `tasks.py`, `recipes.py`); file verbs follow pathlib (`read_bytes`/`read_text`/`read_json`/`write`/`mkdir`). The sync/async surfaces share one *request core* (`transport.RequestSpec` + `_*_spec` builders); shared concerns are isolated: `auth.py`, `host.py`, `paths.py`, `transport.py`, `errors.py`, `models.py` (pydantic v2). Every exception derives from a single root, `PysepalError`. There is **no** legacy `compat.py` / pysepal-v3 shim (dropped — no backwards-compat obligations).

## Testing

- `pytest` + `pytest-asyncio` (auto mode) + `respx` for httpx mocking.
- **Never add tests that hit a real SEPAL host without gating.** Everything in `tests/` is mocked. CI has no SEPAL credentials.
- Run via nox: `nox -s tests` / `nox -s lint` / `nox -s mypy`. mypy is `strict`.

## Commit + release workflow

Conventional Commits are **enforced** by a local `commit-msg` pre-commit hook. Setup is one-time: `pre-commit install --hook-type commit-msg`.

Bumping is **local-only** (no auto-bump workflow):

```bash
cz bump                              # updates pyproject + __init__ + CHANGELOG, tags v<new>
git push && git push --tags
gh release create v<new> --title "v<new>" --notes-from-tag
# → release: published → .github/workflows/release.yml → PyPI via OIDC
```

`major_version_zero = true` is set, so breaking changes bump minor while still on 0.x.

`release.yml` triggers on `release: published` **and** `workflow_dispatch` (manual fallback). It uses PyPI **trusted publishing** (OIDC) — no `PYPI_PASSWORD` secret exists, and adding one would be a regression. All third-party Actions are SHA-pinned.

## Things that already bit us once

- `release: created` fires when a Release is drafted, not when it's published. Use `published`. (Fixed in commit `28c1cc5`.)
- Pushing a tag does not fire `release: *` — only the GitHub Release event does. `gh release create` is the trigger.
- GitHub does not replay missed workflow events. If you commit a workflow file *after* the event fired, the workflow won't run retroactively — use `workflow_dispatch` to recover. (Validated: v0.1.0 shipped to PyPI via `workflow_dispatch` on 2026-05-16 after the original `release: created` filter missed the event.)
- TLS verification is **secure by default**, matched on the parsed host, never a substring. Only `host.docker.internal` is auto-skipped; anything else needs an explicit `verify=False` or membership in `PYSEPAL_INSECURE_TLS_HOSTS` (comma-separated, exact-host match). Do not re-add a hardcoded personal host.

## Files an agent should know

- `HARDENING.md` — security/release setup checklist with current progress
- `STATUS.html` — human-readable project status snapshot
- `noxfile.py` — `lint`, `mypy`, `tests` sessions used by CI and locally
- `pyproject.toml` — `[tool.commitizen]` config; do not change `version_provider` or `version_files` without also updating the release flow
- `.github/workflows/release.yml` — OIDC publish; trigger filter is load-bearing
- `.pre-commit-config.yaml` — only `commit-msg` hook is active; do not add file-modifying hooks without discussion (they conflict with `cz bump`)

## Conventions

- Conventional Commit prefixes: `feat`, `fix`, `chore`, `ci`, `docs`, `refactor`, `test`, `release`. Only `feat`/`fix`/`BREAKING CHANGE` cause version bumps via `cz`.
- Public re-exports go through `src/pysepal_api/__init__.py`. Don't ask users to import from submodules.
- Endpoints follow the same pattern across sync/async: same method names, same arg shapes, only the `await` differs.
- When adding an endpoint method, add it to **both** the sync and async classes in the same PR. `tests/test_async_parity.py` exists to catch drift.

## Out of scope (do not add without discussion)

- Solara / ipywidgets / any UI framework — belongs in `pysepal`.
- A lockfile — this is a library; lockfiles belong in consumer apps.
- Earth Engine auth helpers — different project (`ee-client`).
- A bump workflow that runs in CI — explicit user decision to keep bumps local.
