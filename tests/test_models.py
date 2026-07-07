from datetime import datetime

from pysepal_api.models import (
    DirectoryListing,
    FileEntry,
    RecipeSummary,
    Task,
    TaskState,
)


def test_file_entry_aliases_and_is_dir() -> None:
    entry = FileEntry.model_validate(
        {
            "name": "out",
            "path": "module_results/app/out",
            "type": "directory",
            "size": 0,
            "modifiedTime": "2026-05-14T10:00:00Z",
            "isSymlink": False,
        }
    )
    assert entry.is_dir is True
    assert isinstance(entry.modified_time, datetime)


def test_directory_listing_envelope() -> None:
    listing = DirectoryListing.model_validate({"path": ".", "files": [], "count": 0})
    assert listing.path == "."
    assert listing.files == []


def test_directory_listing_iterates_over_entries() -> None:
    listing = DirectoryListing.model_validate(
        {
            "path": ".",
            "files": [
                {"name": "a", "path": "a", "type": "file", "size": 1},
                {"name": "b", "path": "b", "type": "directory", "size": 0},
            ],
        }
    )
    assert len(listing) == 2
    assert [entry.name for entry in listing] == ["a", "b"]


def test_file_entry_tolerates_unknown_type_values() -> None:
    # Forward-compat: a new server-side `type` must not break parsing.
    entry = FileEntry.model_validate({"name": "s", "path": "s", "type": "socket", "size": 0})
    assert entry.is_dir is False
    assert entry.is_file is False


def test_task_accepts_state_or_status() -> None:
    raw = Task.model_validate({"id": "t1", "state": "ACTIVE"})
    listed = Task.model_validate({"id": "t2", "status": "PENDING"})
    assert raw.state is TaskState.ACTIVE
    assert listed.state is TaskState.PENDING


def test_task_state_enum_includes_canceling() -> None:
    assert TaskState("CANCELING") is TaskState.CANCELING
    assert TaskState("CANCELED") is TaskState.CANCELED


def test_recipe_summary_aliases() -> None:
    s = RecipeSummary.model_validate(
        {
            "id": "r1",
            "projectId": "p1",
            "name": "Demo",
            "type": "CLASSIFICATION",
            "updateTime": "2026-05-01T00:00:00Z",
        }
    )
    assert s.project_id == "p1"
    assert isinstance(s.update_time, datetime)


def test_models_ignore_extra_fields() -> None:
    Task.model_validate({"id": "t", "state": "PENDING", "futureField": 42})
    FileEntry.model_validate(
        {
            "name": "x",
            "path": "x",
            "type": "file",
            "size": 1,
            "newField": True,
        }
    )
