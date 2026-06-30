import pytest
import respx

from pysepal_api import AsyncSepalClient, NoAuth, NotFound


@pytest.mark.asyncio
async def test_async_client_lists() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/user-files/listFiles").respond(
            200, json={"path": ".", "files": [], "count": 0}
        )
        async with AsyncSepalClient(
            base_url="https://sepal.test",
            auth=NoAuth(),
            create_base_dir=False,
        ) as client:
            listing = await client.user_files.list(".")
            assert listing.path == "."


@pytest.mark.asyncio
async def test_async_client_creates_module_dir() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        async with AsyncSepalClient(
            base_url="https://sepal.test",
            auth=NoAuth(),
            module_name="demo",
        ) as client:
            assert str(client.results_path) == ("/home/sepal-user/module_results/demo")


@pytest.mark.asyncio
async def test_async_create_factory_makes_module_dir() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        client = await AsyncSepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        )
        try:
            assert str(client.results_path) == "/home/sepal-user/module_results/demo"
        finally:
            await client.aclose()


@pytest.mark.asyncio
async def test_async_request_escape_hatch() -> None:
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.get("/api/gee/image/json").respond(200, json={"ok": True})
        mock.get("/api/gee/missing").respond(404, text="nope")
        async with AsyncSepalClient(
            base_url="https://sepal.test", auth=NoAuth(), create_base_dir=False
        ) as client:
            resp = await client.get("/api/gee/image/json", params={"recipeId": "foo"})
            assert resp.json() == {"ok": True}
            with pytest.raises(NotFound):
                await client.get("/api/gee/missing")
