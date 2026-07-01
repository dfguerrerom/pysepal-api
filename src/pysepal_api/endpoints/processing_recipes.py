"""SEPAL processing-recipes endpoint.

Confirmed routes (v0):

- `GET    /api/processing-recipes`
- `GET    /api/processing-recipes/{id}`
- `POST   /api/processing-recipes/{id}`            (gzip body + query params)
- `DELETE /api/processing-recipes/{id}`
"""

from __future__ import annotations

import gzip
import json
from typing import Any, Literal, overload

from ..models import RecipeSummary
from ..transport import RequestSpec, parse_many
from ..transport import parse_json as _parse_json
from ._base import _AsyncEndpoint, _SyncEndpoint

# Defined at module scope, where `list` is the builtin — the endpoint method
# named `list` would otherwise shadow it inside the class body annotations.
RecipeContents = bytes | str | dict[str, Any] | list[Any]
RecipeSummaries = list[RecipeSummary]


def _save_spec(
    recipe_id: str,
    project_id: str,
    type: str,
    name: str,
    contents: RecipeContents,
) -> RequestSpec:
    if isinstance(contents, (dict, list)):
        raw = json.dumps(contents).encode("utf-8")
    elif isinstance(contents, str):
        raw = contents.encode("utf-8")
    else:
        raw = contents
    return RequestSpec(
        "POST",
        f"/api/processing-recipes/{recipe_id}",
        params={"projectId": project_id, "type": type, "name": name},
        content=gzip.compress(raw),
        headers={"Content-Type": "application/gzip"},
    )


def _summaries(resp: Any) -> RecipeSummaries:
    return parse_many(resp, RecipeSummary)


class ProcessingRecipesEndpoint(_SyncEndpoint):
    def list(self) -> RecipeSummaries:
        return _summaries(self._send(RequestSpec("GET", "/api/processing-recipes")))

    @overload
    def get(self, recipe_id: str, *, parse_json: Literal[True] = True) -> Any: ...
    @overload
    def get(self, recipe_id: str, *, parse_json: Literal[False]) -> bytes: ...

    def get(self, recipe_id: str, *, parse_json: bool = True) -> Any:
        """Load a recipe. Returns the parsed JSON body unless `parse_json=False`."""
        resp = self._send(RequestSpec("GET", f"/api/processing-recipes/{recipe_id}"))
        return _parse_json(resp) if parse_json else resp.content

    def save(
        self,
        recipe_id: str,
        *,
        project_id: str,
        type: str,
        name: str,
        contents: RecipeContents,
    ) -> RecipeSummaries:
        """POST a recipe. SEPAL stores the gzipped body as-is; pass either
        already-encoded bytes/str or a JSON-serializable structure that the
        client will encode for you."""
        return _summaries(self._send(_save_spec(recipe_id, project_id, type, name, contents)))

    def delete(self, recipe_id: str) -> RecipeSummaries:
        return _summaries(self._send(RequestSpec("DELETE", f"/api/processing-recipes/{recipe_id}")))


class AsyncProcessingRecipesEndpoint(_AsyncEndpoint):
    async def list(self) -> RecipeSummaries:
        return _summaries(await self._send(RequestSpec("GET", "/api/processing-recipes")))

    @overload
    async def get(self, recipe_id: str, *, parse_json: Literal[True] = True) -> Any: ...
    @overload
    async def get(self, recipe_id: str, *, parse_json: Literal[False]) -> bytes: ...

    async def get(self, recipe_id: str, *, parse_json: bool = True) -> Any:
        resp = await self._send(RequestSpec("GET", f"/api/processing-recipes/{recipe_id}"))
        return _parse_json(resp) if parse_json else resp.content

    async def save(
        self,
        recipe_id: str,
        *,
        project_id: str,
        type: str,
        name: str,
        contents: RecipeContents,
    ) -> RecipeSummaries:
        return _summaries(await self._send(_save_spec(recipe_id, project_id, type, name, contents)))

    async def delete(self, recipe_id: str) -> RecipeSummaries:
        return _summaries(
            await self._send(RequestSpec("DELETE", f"/api/processing-recipes/{recipe_id}"))
        )
