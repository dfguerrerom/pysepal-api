import asyncio
import inspect

import pytest

from pysepal_api.endpoints.processing_recipes import (
    AsyncProcessingRecipesEndpoint,
    ProcessingRecipesEndpoint,
)
from pysepal_api.endpoints.tasks import AsyncTasksEndpoint, TasksEndpoint
from pysepal_api.endpoints.user_files import (
    AsyncUserFilesEndpoint,
    UserFilesEndpoint,
)

PAIRS = [
    (UserFilesEndpoint, AsyncUserFilesEndpoint),
    (TasksEndpoint, AsyncTasksEndpoint),
    (ProcessingRecipesEndpoint, AsyncProcessingRecipesEndpoint),
]


@pytest.mark.parametrize("sync, async_", PAIRS)
def test_method_names_match(sync: type, async_: type) -> None:
    sync_methods = {
        name
        for name, value in vars(sync).items()
        if callable(value) and not name.startswith("_")
    }
    async_methods = {
        name
        for name, value in vars(async_).items()
        if (callable(value) or inspect.iscoroutinefunction(value))
        and not name.startswith("_")
    }
    assert sync_methods == async_methods


@pytest.mark.parametrize("_, async_", PAIRS)
def test_async_methods_are_coroutines(_: type, async_: type) -> None:
    for name, value in vars(async_).items():
        if name.startswith("_"):
            continue
        assert inspect.iscoroutinefunction(value), name
