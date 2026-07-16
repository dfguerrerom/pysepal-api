# TaskManager EE Export Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Reconciled 2026-07-16.** This plan was originally written 2026-05-18. Since
> then the SEPAL side was partially built on branch `feat/taskmanager-ee-export`
> and has **outgrown the original plan's JS sketches**. Key changes in this
> refresh:
> - The **branch's `eeExport.js` is the source of truth** for the payload
>   contract (it adds `crs`/`crsTransform`/`shardSize`/`formatOptions`, GCS-vs-Drive
>   routing, and resolves `workspacePath` against the user's home dir with `..`
>   traversal guards — the original sketch passed it through raw).
> - The pysepal-api helpers (Tasks 1–3) were **never implemented** and remain
>   the real remaining pysepal-api work, now retargeted at the branch contract.
> - The former SEPAL implementation tasks become a single **review → rebase →
>   merge** task (Task 4) — do not re-implement from sketches.
> - The former pysepal Solara integration task is **removed** from this plan and
>   split to a downstream follow-up (see Rollout); it depends on a pysepal-api
>   release landing first.
> - The **read** direction (`recipes.get_image`) and recipe-creation ideas are
>   *not* in this plan — see
>   `docs/superpowers/specs/2026-07-16-ee-image-read-design.md`.

**Goal:** Route notebook-created `ee.Image` and `ee.FeatureCollection` exports from pysepal-api through SEPAL TaskManager using one task operation (`ee.export`) and the existing `POST /api/tasks` route.

**Architecture:** `pysepal-api` builds a typed `ee.export` task payload by serializing EE objects into Cloud API expressions, then submits it through `SepalClient.tasks.submit(...)`. SEPAL's `ee.export` worker (on `feat/taskmanager-ee-export`) decodes the expression and dispatches by `kind` (`IMAGE`, `TABLE`) and `destination` (`GEE`, `DRIVE`, `SEPAL`) to reusable image/table export jobs.

**API decisions (confirmed 2026-07-16):**
- Per-kind methods `submit_image` / `submit_table` on a dedicated
  `client.ee_exports` endpoint (alias `client.exports`). Not a single
  `export_ee_image(...)`.
- `TABLE` is **in scope** (the SEPAL branch already supports it).
- No pysepal (Solara) changes in this plan.

**Tech Stack:** Python 3.10–3.12, httpx, pydantic v2, pytest/respx, Earth Engine Python serializer, SEPAL Node task worker (existing branch), Jest.

---

## Contract (source of truth: branch `eeExport.js`)

All exports submit this shape through `POST /api/tasks`:

```json
{
  "operation": "ee.export",
  "params": {
    "title": "Export ndvi_2026 to SEPAL",
    "description": "ndvi_2026",
    "export": {
      "kind": "IMAGE",
      "destination": "SEPAL",
      "expression": {"values": {}, "result": "0"},
      "region": {"values": {}, "result": "1"},
      "scale": 30,
      "crs": "EPSG:4326",
      "crsTransform": null,
      "dimensions": null,
      "maxPixels": 10000000000000,
      "shardSize": null,
      "fileDimensions": null,
      "skipEmptyTiles": null,
      "fileFormat": "GEO_TIFF",
      "formatOptions": null,
      "retries": null,
      "assetId": "projects/my-project/assets/exports/ndvi_2026",
      "assetType": "Image",
      "pyramidingPolicy": null,
      "sharing": null,
      "strategy": null,
      "tileSize": null,
      "properties": {},
      "workspacePath": "module_results/my_module/exports",
      "driveFolder": "SEPAL/exports",
      "filenamePrefix": "ndvi_2026",
      "selectors": ["id"],
      "maxVertices": 1000000
    },
    "taskInfo": {
      "destination": "SEPAL",
      "outputPath": "module_results/my_module/exports",
      "source": "pysepal-api",
      "kind": "IMAGE"
    }
  }
}
```

Rules:

- Public route stays `POST /api/tasks`; no new HTTP endpoint. Worker operation is exactly `ee.export`.
- `kind` ∈ {`IMAGE`, `TABLE`}. `destination` ∈ {`GEE`, `DRIVE`, `SEPAL`}.
- `expression` and `region` are Earth Engine **Cloud API expression dicts, not strings** — build with `ee.serializer.encode(obj, for_cloud_api=True)`.
- `fileFormat` uses Python-side canonical values (`GEO_TIFF`); the SEPAL worker maps image `GEO_TIFF` → JS `GeoTIFF`.
- **`workspacePath` is relative to the user's SEPAL home dir.** The branch worker resolves it against `homeDir` and rejects `..` traversal — never send an absolute path.
- Destination-specific keys: `GEE` → `assetId` (required), plus optional `assetType`/`sharing`/`strategy`/`pyramidingPolicy`/`tileSize`/`properties`; `DRIVE` → `driveFolder`; `SEPAL` → `workspacePath`. Table-only: `selectors`, `maxVertices`.
- Emit only keys with values; omit `None` (the builder cleans them).
- `taskInfo.outputPath` is the conflict-detection key used by `/api/tasks?outputPath=...&destination=...` filtering; set it to `assetId` / `workspacePath` / `driveFolder` / `filenamePrefix` / `name` (first non-empty).

## Remaining work overview

| Task | Repo | State |
|---|---|---|
| 1. Export payload builder (sync) | pysepal-api | to build |
| 2. Async wrapper + client wiring + `[ee]` extra | pysepal-api | to build |
| 3. Python contract test | pysepal-api | to build |
| 4. Review + rebase + merge SEPAL branch | sepal | branch partially built |
| 5. pysepal-api docs | pysepal-api | to build |

---

### Task 1: pysepal-api Export Payload Builder (sync)

**Files:** Create `src/pysepal_api/endpoints/ee_exports.py`; Test `tests/endpoints/test_ee_exports_submit.py`.

- [ ] **Step 1: Write failing sync tests** covering image→SEPAL and table→GEE. Assert `operation == "ee.export"`, the full `export` dict (matching the Contract above, `None`s omitted), and `taskInfo` (`source == "pysepal-api"`, `outputPath` resolution). Use `respx` to mock `POST /api/tasks`.

- [ ] **Step 2: Run to confirm failure** (`nox -s tests -- tests/endpoints/test_ee_exports_submit.py -q`) → `ModuleNotFoundError`.

- [ ] **Step 3: Implement the sync wrapper.** `EEExportsEndpoint(tasks: TasksEndpoint)` with:
  - `EEExportDestination`/`EEExportKind` str-enums.
  - `serialize_ee_object(value) -> dict[str, Any]`: pass a `Mapping` through unchanged (already an expression dict); otherwise lazy-import `ee` and return `ee.serializer.encode(value, for_cloud_api=True)`, raising `MissingDependency` (root: `PysepalError`) with the `pip install pysepal-api[ee]` hint on `ImportError`.
  - `submit_image(*, image, destination, name, region=None, scale=None, crs=None, crs_transform=None, dimensions=None, max_pixels=10_000_000_000_000, shard_size=None, file_dimensions=None, skip_empty_tiles=None, file_format="GEO_TIFF", format_options=None, retries=None, asset_id=None, asset_type=None, sharing=None, strategy=None, pyramiding_policy=None, tile_size=None, properties=None, workspace_path=None, drive_folder=None, filename_prefix=None, instance_type=None) -> Task`.
  - `submit_table(*, collection, destination, name, asset_id=None, workspace_path=None, drive_folder=None, filename_prefix=None, file_format="SHP", selectors=None, max_vertices=None, strategy=None, instance_type=None) -> Task`.
  - Both delegate to a shared `_build_params(...)` that assembles `export` (camelCase keys, `None` omitted via a `_clean` filter) + `taskInfo`, then calls `self._tasks.submit(operation="ee.export", params=..., instance_type=...)`. Return the un-waited `Task`.
  - Validate required args early (GEE needs `asset_id`) and raise `ValueError` before serialization/network.

- [ ] **Step 4: Run the sync tests** → PASS.

- [ ] **Step 5: Commit** (`feat: add TaskManager EE export payload builder`).

### Task 2: Async Wrapper + Client Wiring + `[ee]` Extra

**Files:** Modify `src/pysepal_api/endpoints/ee_exports.py`, `client.py`, `__init__.py`, `pyproject.toml`; Test `tests/endpoints/test_async_ee_exports_submit.py`, `tests/test_async_parity.py`.

- [ ] **Step 1: Write failing async test** (image→DRIVE) importing `AsyncEEExportsEndpoint`.
- [ ] **Step 2: Confirm failure.**
- [ ] **Step 3: Implement async wrapper without duplicating payload logic.** Factor `_build_params(*, kind, object_key, kwargs)` at module scope; `EEExportsEndpoint` and `AsyncEEExportsEndpoint` both call it and differ only by `await self._tasks.submit(...)`.
- [ ] **Step 4: Wire clients.** In `SepalClient.__init__` after `self.tasks = TasksEndpoint(...)`: `self.ee_exports = EEExportsEndpoint(self.tasks)` and alias `self.exports = self.ee_exports`. Mirror in `AsyncSepalClient` with the async classes.
- [ ] **Step 5: Re-export** `AsyncEEExportsEndpoint`, `EEExportsEndpoint`, `EEExportDestination`, `EEExportKind`, `serialize_ee_object`, `MissingDependency` from `__init__.py` and add to `__all__`.
- [ ] **Step 6: `pyproject.toml`** — add `[project.optional-dependencies] ee = ["earthengine-api>=1.5"]`; add an `ee.*` mypy `ignore_missing_imports` override (strict mode, no stubs).
- [ ] **Step 7: Async parity** — extend `tests/test_async_parity.py` to assert the sync/async `ee_exports` public method sets match.
- [ ] **Step 8: Verify** — `nox -s tests`, `nox -s lint`, `nox -s mypy` all pass.
- [ ] **Step 9: Commit** (`feat: expose TaskManager EE export helpers`).

### Task 3: Python Contract Test

**Files:** Create `tests/endpoints/test_ee_exports_contract.py`.

- [ ] Assert the emitted payload for image→SEPAL and table→GEE equals a golden derived from the **branch's** `eeExport.contract.test.js` (so any client/server drift breaks a unit test). The JS side of the contract already exists on the branch — do **not** add a new JS contract test here.
- [ ] Run → PASS; commit (`test: lock EE export task contract`).

### Task 4: SEPAL Branch — Clean Rebase, ESM Port, Merge

**Repo:** `sepal` (worktree `/home/dguerrero/sepal/worktrees/taskmanager-ee-export`, branch `feat/taskmanager-ee-export`).

> This replaces the original plan's "implement `eeExport.js` / `toTable.js`" tasks — that code already exists (as loose work in the worktree).

- [x] **Step 1: Clean rebase onto master** (done 2026-07-16). The work was uncommitted on a base 104 commits stale; snapshotted to tag `backup/ee-export-presnapshot-2026-07-16`, rebased onto `origin/master`, resolved the one-line `taskRunner.js` conflict (master now uses ESM `require('./tasks/x.js')` form), and committed as `feat(task): add generic ee.export worker for IMAGE/TABLE exports` (`2b4eaf3e6`).
- [ ] **Step 2: CommonJS → ESM port (blocking).** Master migrated the task module to ESM (`modules/task/package.json` → `"type": "module"`; siblings use `import`/`export`). The new files are still CommonJS and will not load. Convert `eeExport.js`, `eeExport.test.js`, `eeExport.contract.test.js`, `toTable.js`, `toTable.test.js`: `require(...)` → `import ... from '...js'`, `module.exports = {...}` → `export const ...`, add `.js` extensions on relative specifiers. (The `toDrive.js`/`toSepal.js` edits auto-merged into the ESM files and are fine.)
- [ ] **Step 3: Run the task tests** (`cd modules/task && npm test -- eeExport.test.js eeExport.contract.test.js toTable.test.js`) and lint. Confirm every key the pysepal-api builder emits is consumed and `workspacePath` home-dir resolution + `..` guard behave as documented.
- [ ] **Step 4: Merge/deploy** so `ee.export` is live before pysepal-api helpers are released against production SEPAL. (Rebasing any *other* in-progress working branch onto this is a separate, user-driven step — not part of this task.)

### Task 5: Documentation

**Files:** Modify `README.md` (and/or the docs site guides).

- [ ] Document `SepalClient.ee_exports.submit_image(...)` / `submit_table(...)` with a notebook example for all three destinations; note `[ee]` extra and that `workspace_path` is relative to the SEPAL home dir.
- [ ] Commit (`docs: document TaskManager EE exports`).

## Rollout Notes

- Land SEPAL worker support (Task 4) before releasing pysepal-api helpers that notebooks call against production SEPAL.
- Release `pysepal-api` after Tasks 2–3 pass.
- **Follow-up (out of this plan): pysepal Solara `export_engine` integration.** Route session-backed Solara exports through `SepalClient.ee_exports` once a pysepal-api release is available in the SEPAL app environment. Its own spec/plan.
- Live export validation requires real SEPAL + Earth Engine credentials; ask before running those tests (they submit external work).

## Self-Review

- Coverage: one `/api/tasks` route, one `ee.export` operation, IMAGE/TABLE, GEE/DRIVE/SEPAL, pysepal-api helper + wiring + `[ee]` extra, contract test, SEPAL branch merge.
- Contract keys match the branch worker; `workspacePath` documented as home-relative with `..` guard.
- Scope: pysepal Solara split to follow-up; read direction + recipe-creation covered by the separate 2026-07-16 read-design spec.
