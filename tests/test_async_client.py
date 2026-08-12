import pytest
import respx

from pysepal_api import AsyncSepalClient, NoAuth, NotFound


@pytest.mark.asyncio
async def test_async_client_lists() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/listFiles").respond(
            200, json={"path": ".", "files": [], "count": 0}
        )
        async with AsyncSepalClient(base_url="https://sepal.test", auth=NoAuth()) as client:
            listing = await client.files.list(".")
            assert listing.path == "."


@pytest.mark.asyncio
async def test_async_request_escape_hatch() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/gee/image/json").respond(200, json={"ok": True})
        mock.get("/api/gee/missing").respond(404, text="nope")
        async with AsyncSepalClient(base_url="https://sepal.test", auth=NoAuth()) as client:
            resp = await client.get("/api/gee/image/json", params={"recipeId": "foo"})
            assert resp.json() == {"ok": True}
            with pytest.raises(NotFound):
                await client.get("/api/gee/missing")
