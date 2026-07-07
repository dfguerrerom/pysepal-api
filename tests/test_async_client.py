import pytest
import respx

from pysepal_api import AsyncSepalClient, NoAuth, NotFound, Unauthorized


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
async def test_async_create_can_be_awaited() -> None:
    """Long-lived form: `sepal = await AsyncSepalClient.create(...)`."""
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
async def test_async_create_works_as_context_manager() -> None:
    """Scoped form: `async with AsyncSepalClient.create(...)` — no `await` needed,
    mirroring the sync spelling exactly."""
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(200, json={})
        async with AsyncSepalClient.create(
            base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
        ) as client:
            assert str(client.results_path) == "/home/sepal-user/module_results/demo"
        assert client._http.is_closed


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


@pytest.mark.asyncio
async def test_async_create_closes_client_if_module_dir_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = {"n": 0}
    real_aclose = AsyncSepalClient.aclose

    async def spy(self: AsyncSepalClient) -> None:
        closed["n"] += 1
        await real_aclose(self)

    monkeypatch.setattr(AsyncSepalClient, "aclose", spy)
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(401, text="nope")
        with pytest.raises(Unauthorized):
            await AsyncSepalClient.create(
                base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
            )
    assert closed["n"] == 1


@pytest.mark.asyncio
async def test_async_context_manager_closes_client_if_module_dir_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = {"n": 0}
    real_aclose = AsyncSepalClient.aclose

    async def spy(self: AsyncSepalClient) -> None:
        closed["n"] += 1
        await real_aclose(self)

    monkeypatch.setattr(AsyncSepalClient, "aclose", spy)
    with respx.mock(base_url="https://sepal.test") as mock:
        mock.post("/api/user-files/createFolder").respond(401, text="nope")
        with pytest.raises(Unauthorized):
            async with AsyncSepalClient(
                base_url="https://sepal.test", auth=NoAuth(), module_name="demo"
            ):
                pass
    assert closed["n"] == 1
