"""Pydantic v2 models for SEPAL responses.

All models accept extra fields silently so SEPAL adding payload keys does not
break clients. Field aliases mirror SEPAL's `camelCase` wire format while
exposing Pythonic `snake_case` attributes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TaskState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELING = "CANCELING"
    CANCELED = "CANCELED"
    FAILED = "FAILED"


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class FileEntry(_Base):
    name: str
    path: str
    type: Literal["directory", "file", "symlink"]
    size: int
    modified_time: datetime | None = Field(default=None, alias="modifiedTime")
    is_symlink: bool = Field(default=False, alias="isSymlink")

    @property
    def is_dir(self) -> bool:
        return self.type == "directory"


class DirectoryListing(_Base):
    path: str
    files: list[FileEntry]
    count: int | None = None


class Task(_Base):
    id: str
    recipe_id: str | None = Field(default=None, alias="recipeId")
    name: str | None = None
    operation: str | None = None
    state: TaskState = Field(validation_alias=AliasChoices("state", "status"))
    status_description: str | None = Field(default=None, alias="statusDescription")
    params: dict[str, Any] | None = None
    task_info: dict[str, Any] | None = Field(default=None, alias="taskInfo")
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    update_time: datetime | None = Field(default=None, alias="updateTime")


class RecipeSummary(_Base):
    id: str
    project_id: str | None = Field(default=None, alias="projectId")
    name: str
    type: str
    creation_time: datetime | None = Field(default=None, alias="creationTime")
    update_time: datetime | None = Field(default=None, alias="updateTime")


class FileWriteResult(_Base):
    """Server response from `setFile`. Shape is loose; we keep raw fields."""

    path: str | None = None
    size: int | None = None
