# Design: `recipes.get_image()` — SEPAL recipe → `ee.Image`

**Date:** 2026-07-16
**Status:** Design — pending review
**Companion:** export direction is covered by
`docs/superpowers/plans/2026-05-18-taskmanager-ee-export-integration.md`
(refreshed 2026-07-16).

## Summary

Add `client.recipes.get_image(recipe_id) -> ee.Image` to pysepal-api: fetch a
SEPAL processing recipe's Earth Engine expression and rehydrate it into a live
`ee.Image` object in the caller's Python session. This is the **read** half of
the GEE ↔ SEPAL image bridge; the **write** half (`ee.Image` → SEPAL export)
lives in the companion export plan.

## Context

Both directions of the bridge speak one currency: a **serialized Earth Engine
Cloud API expression** (a `dict`, not a string).

- **Write:** `ee.serializer.encode(image, for_cloud_api=True)` → payload → SEPAL
  `ee.export` task → SEPAL decodes with `ee.Deserializer.decodeCloudApi`.
- **Read (this spec):** SEPAL already exposes
  `GET /api/gee/image/json?recipeId=<id>`, whose worker does
  `loadRecipe → ImageFactory(recipe).getImage$() → image.serialize()` and
  returns the serialized expression. Python fetches it and deserializes to an
  `ee.Image`.

**The recipe → image reconstruction happens server-side, inside SEPAL's
`imageFactory`.** pysepal-api does **not** port SEPAL's recipe types. This is
why the read direction is small.

**Readiness:** `GET /api/gee/image/json` is already on SEPAL `master` (verified
2026-07-16). This spec has **no SEPAL-side dependency** and can ship
independently of the export branch.

## Scope

**In:**
- `recipes.get_image(recipe_id) -> ee.Image` (sync + async parity).
- The shared `pysepal-api[ee]` optional extra + lazy `ee` import, if not already
  added by the export effort. Whichever effort lands first owns the wiring; the
  other reuses it.

**Out:**
- Earth Engine authentication. The caller initializes `ee` themselves (matches
  the repo's "no EE auth helpers" rule; that is `ee-client`'s job).
- Recipe-type-specific logic in Python — SEPAL owns it.
- Any recipe *creation* from an `ee.Image` — see Future Directions.

## Design

### Public method

```python
# on RecipesEndpoint / AsyncRecipesEndpoint
def get_image(self, recipe_id: str) -> "ee.Image": ...
```

Placement on `recipes` reads naturally ("load this recipe as an image") even
though the underlying route is under `/api/gee`. Returns a live `ee.Image`.

### Flow

1. `GET /api/gee/image/json?recipeId=<recipe_id>` via the existing request core
   (`RequestSpec` + `_send`), typed-error mapped like every other endpoint.
2. Read the response body (the serialized Cloud API expression).
3. Deserialize into an `ee.Image` via `ee.deserializer` (lazy import).
4. Return the `ee.Image`.

### Request core (repo convention)

Add a pure spec builder reused by both surfaces:

```python
def _get_image_spec(recipe_id: str) -> RequestSpec:
    return RequestSpec("GET", "/api/gee/image/json", params={"recipeId": recipe_id})
```

Sync/async methods differ only by `await self._send(...)`, matching every other
endpoint. `tests/test_async_parity.py` covers name/coroutine drift.

### Deserialization — the one detail to pin during implementation

SEPAL's worker returns JavaScript `image.serialize()`. The exact Python
`earthengine-api` entrypoint that consumes it — `ee.deserializer.fromJSON(text)`
vs `ee.deserializer.decode(json.loads(text))` vs a Cloud-API variant — depends
on whether the payload is the legacy or Cloud API JSON shape. **This must be
verified against a live sample during implementation** (fetch one real recipe's
`/api/gee/image/json` output and confirm which call round-trips it). The design
is otherwise agnostic; only the single deserializer call is unknown.

Isolate it behind a helper so the choice lives in one place:

```python
# _ee.py (shared with the export effort)
def _require_ee():
    try:
        import ee  # noqa: F401
        return ee
    except ImportError as exc:
        raise MissingDependency(
            "recipes.get_image() requires Earth Engine. Install with "
            "`pip install pysepal-api[ee]`."
        ) from exc

def _deserialize_image(payload: bytes | str):
    ee = _require_ee()
    # pinned against a live sample during implementation:
    return ee.deserializer.fromJSON(payload if isinstance(payload, str) else payload.decode())
```

`MissingDependency` derives from the existing `PysepalError` root (new error
type; carries the install hint).

### `[ee]` optional extra

```toml
[project.optional-dependencies]
ee = ["earthengine-api>=1.5"]
```

Core install stays httpx + pydantic only; `ee` loads lazily, and only when
`get_image` (or an export helper) is actually called. mypy strict: add an
`ee.*` `ignore_missing_imports` override (no stubs).

### Errors & return

- Recipe not found / not authorized → the normal typed `ApiError` subtree from
  the request core (no special handling).
- `ee` missing → `MissingDependency` with the install hint, raised **before**
  any network call where practical.
- Returns a live `ee.Image`. No implicit `.getInfo()` or evaluation.

## Testing

- `respx`-mock `GET /api/gee/image/json`; assert the request carries
  `recipeId`, and that a captured serialized-expression fixture round-trips to a
  non-null `ee.Image` (`.bandNames().getInfo()` gated behind
  `pytest.importorskip("ee")` and only where an EE session is available — most
  assertions check the request + that deserialize was invoked, not live EE).
- Pure `_get_image_spec` test (no `ee`).
- Async parity via `tests/test_async_parity.py`.
- No test hits a real SEPAL host (repo rule).

## Future Directions — recipe *creation* from an `ee.Image`

Creating a SEPAL recipe *from* a computed `ee.Image` is deliberately **out of
this spec**. Two paths exist; both warrant their own decision, and one is a
SEPAL feature.

### A. Asset-compose (works today, no SEPAL change)

`ee_exports.submit_image(destination="GEE", asset_id=…)` → wait → 
`recipes.save(type="ASSET", …)` pointing at the new asset.

- **Pro:** implementable now against existing SEPAL (`ASSET` recipe type +
  `/api/tasks` already exist).
- **Con:** it **freezes** the computation into a static raster. A computed
  `ee.Image` is not an asset; this discards the dynamic object and calls the
  pointer a "recipe." The ASSET recipe `{type, model:{…}}` schema is also
  GUI-owned and drifts, so it needs a fixture pinned to a captured real recipe.

### B. `EE_EXPRESSION` recipe type (new SEPAL feature — own brainstorm)

Add a SEPAL recipe type whose stored content **is** the serialized Cloud API
expression. `imageFactory` gains a ~one-line handler:
`ee.Deserializer.decodeCloudApi(recipe.expression) → ee.Image`. Then everything
SEPAL already does with recipes — preview tiles, `ee.export`, this spec's
`get_image` round-trip — works on arbitrary externally-computed EE objects:
*"run external JS/Python, persist the computation as a recipe, render/export it
on SEPAL."* Symmetric with the export direction; preserves the dynamic object
instead of freezing it.

Open questions that make this its own brainstorm (SEPAL + pysepal-api), not a
bolt-on:
- **GUI tolerance:** the SEPAL GUI must not break on an unknown recipe type; a
  headless-only MVP (create + read programmatically, no GUI panel) may be
  viable first.
- **Recipe model/validation:** what minimal `{type, model}` the backend accepts.
- **Credentials at render time:** a stored expression may reference the user's
  *private* assets — whose EE identity renders it (SEPAL service account vs the
  user)?
- **Staleness:** serialized expressions are tied to EE's expression format and
  any referenced assets; both can drift/vanish. Versioning/expiry story.

**Recommendation:** ship `get_image` now; open `EE_EXPRESSION` as a separate
SEPAL-side brainstorm. Reach for asset-compose only if a concrete need for
"image → recipe" lands before `EE_EXPRESSION` is designed.
