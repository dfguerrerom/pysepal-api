"""Earth Engine export helper endpoint.

Routes notebook-created ``ee.Image`` / ``ee.FeatureCollection`` exports through
SEPAL's TaskManager using the single ``ee.export`` task operation and the
existing ``POST /api/tasks`` route (via :class:`~pysepal_api.endpoints.tasks`).

The payload contract mirrors the SEPAL ``ee.export`` worker: a typed ``export``
block plus a ``taskInfo`` block. ``expression``/``region`` are Earth Engine
**Cloud API expression dicts** (from ``ee.serializer.encode(obj,
for_cloud_api=True)``), never strings. Only keys with values are emitted.

``serialize_ee_object`` accepts an already-encoded expression dict unchanged, so
callers (and tests) can pass expression dicts without ``earthengine-api``
installed; encoding a live ``ee`` object lazily imports ``ee`` and raises
:class:`~pysepal_api.errors.MissingDependency` (install the ``[ee]`` extra) when
it is missing.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from ..errors import MissingDependency
from ..models import Task
from .tasks import TasksEndpoint

_SOURCE = "pysepal-api"
_INSTALL_HINT = "install the Earth Engine extra with `pip install pysepal-api[ee]`"


class EEExportKind(str, Enum):
    IMAGE = "IMAGE"
    TABLE = "TABLE"


class EEExportDestination(str, Enum):
    GEE = "GEE"
    DRIVE = "DRIVE"
    SEPAL = "SEPAL"


def serialize_ee_object(value: Any) -> dict[str, Any]:
    """Return a Cloud API expression dict for ``value``.

    A :class:`~collections.abc.Mapping` is assumed to already be an encoded
    expression dict and is returned as a plain ``dict`` copy unchanged. Anything
    else is treated as a live Earth Engine object and encoded via
    ``ee.serializer.encode(value, for_cloud_api=True)``; if ``earthengine-api``
    is not installed this raises :class:`~pysepal_api.errors.MissingDependency`.
    """
    if isinstance(value, Mapping):
        return dict(value)
    try:
        import ee  # lazy: earthengine-api is an optional extra
    except ImportError as exc:
        raise MissingDependency(
            f"serializing an Earth Engine object requires earthengine-api; {_INSTALL_HINT}"
        ) from exc
    encoded: dict[str, Any] = ee.serializer.encode(value, for_cloud_api=True)
    return encoded


def _coerce_destination(value: EEExportDestination | str) -> EEExportDestination:
    if isinstance(value, EEExportDestination):
        return value
    return EEExportDestination(str(value).upper())


def _clean(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is ``None`` (the wire omits absent fields)."""
    return {key: value for key, value in fields.items() if value is not None}


def _resolve_output_path(export: Mapping[str, Any], name: str) -> str:
    """Conflict-detection key: first non-empty of assetId / workspacePath /
    driveFolder / filenamePrefix, else the export name."""
    for key in ("assetId", "workspacePath", "driveFolder", "filenamePrefix"):
        value = export.get(key)
        if value:
            return str(value)
    return name


def _build_params(
    *,
    kind: EEExportKind,
    destination: EEExportDestination,
    name: str,
    export_fields: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble the ``params`` block for a ``ee.export`` task.

    ``export_fields`` carries the destination/kind-specific camelCase keys
    (``None`` values are dropped); ``kind`` and ``destination`` are added and
    the ``taskInfo`` block is derived.
    """
    export: dict[str, Any] = {
        "kind": kind.value,
        "destination": destination.value,
        **_clean(export_fields),
    }
    return {
        "title": f"Export {name} to {destination.value}",
        "description": name,
        "export": export,
        "taskInfo": {
            "destination": destination.value,
            "outputPath": _resolve_output_path(export, name),
            "source": _SOURCE,
            "kind": kind.value,
        },
    }


def _image_export_fields(
    *,
    image: Any,
    region: Any,
    scale: float | None,
    crs: str | None,
    crs_transform: list[float] | None,
    dimensions: str | int | None,
    max_pixels: int | None,
    shard_size: int | None,
    file_dimensions: int | list[int] | None,
    skip_empty_tiles: bool | None,
    file_format: str | None,
    format_options: dict[str, Any] | None,
    retries: int | None,
    asset_id: str | None,
    asset_type: str | None,
    sharing: str | None,
    strategy: str | None,
    pyramiding_policy: str | dict[str, str] | None,
    tile_size: int | None,
    properties: dict[str, Any] | None,
    workspace_path: str | None,
    drive_folder: str | None,
    filename_prefix: str | None,
) -> dict[str, Any]:
    return {
        "expression": serialize_ee_object(image),
        "region": serialize_ee_object(region) if region is not None else None,
        "scale": scale,
        "crs": crs,
        "crsTransform": crs_transform,
        "dimensions": dimensions,
        "maxPixels": max_pixels,
        "shardSize": shard_size,
        "fileDimensions": file_dimensions,
        "skipEmptyTiles": skip_empty_tiles,
        "fileFormat": file_format,
        "formatOptions": format_options,
        "retries": retries,
        "assetId": asset_id,
        "assetType": asset_type,
        "sharing": sharing,
        "strategy": strategy,
        "pyramidingPolicy": pyramiding_policy,
        "tileSize": tile_size,
        "properties": properties,
        "workspacePath": workspace_path,
        "driveFolder": drive_folder,
        "filenamePrefix": filename_prefix,
    }


def _table_export_fields(
    *,
    collection: Any,
    asset_id: str | None,
    workspace_path: str | None,
    drive_folder: str | None,
    filename_prefix: str | None,
    file_format: str | None,
    selectors: list[str] | None,
    max_vertices: int | None,
    strategy: str | None,
) -> dict[str, Any]:
    return {
        "expression": serialize_ee_object(collection),
        "fileFormat": file_format,
        "assetId": asset_id,
        "strategy": strategy,
        "workspacePath": workspace_path,
        "driveFolder": drive_folder,
        "filenamePrefix": filename_prefix,
        "selectors": selectors,
        "maxVertices": max_vertices,
    }


def _require_asset_id(destination: EEExportDestination, asset_id: str | None) -> None:
    if destination is EEExportDestination.GEE and not asset_id:
        raise ValueError("asset_id is required when destination is GEE")


def _image_params(
    *,
    destination: EEExportDestination | str,
    name: str,
    image: Any,
    region: Any = None,
    scale: float | None = None,
    crs: str | None = None,
    crs_transform: list[float] | None = None,
    dimensions: str | int | None = None,
    max_pixels: int | None = 10_000_000_000_000,
    shard_size: int | None = None,
    file_dimensions: int | list[int] | None = None,
    skip_empty_tiles: bool | None = None,
    file_format: str | None = "GEO_TIFF",
    format_options: dict[str, Any] | None = None,
    retries: int | None = None,
    asset_id: str | None = None,
    asset_type: str | None = None,
    sharing: str | None = None,
    strategy: str | None = None,
    pyramiding_policy: str | dict[str, str] | None = None,
    tile_size: int | None = None,
    properties: dict[str, Any] | None = None,
    workspace_path: str | None = None,
    drive_folder: str | None = None,
    filename_prefix: str | None = None,
) -> dict[str, Any]:
    dest = _coerce_destination(destination)
    _require_asset_id(dest, asset_id)
    export_fields = _image_export_fields(
        image=image,
        region=region,
        scale=scale,
        crs=crs,
        crs_transform=crs_transform,
        dimensions=dimensions,
        max_pixels=max_pixels,
        shard_size=shard_size,
        file_dimensions=file_dimensions,
        skip_empty_tiles=skip_empty_tiles,
        file_format=file_format,
        format_options=format_options,
        retries=retries,
        asset_id=asset_id,
        asset_type=asset_type,
        sharing=sharing,
        strategy=strategy,
        pyramiding_policy=pyramiding_policy,
        tile_size=tile_size,
        properties=properties,
        workspace_path=workspace_path,
        drive_folder=drive_folder,
        filename_prefix=filename_prefix,
    )
    return _build_params(
        kind=EEExportKind.IMAGE, destination=dest, name=name, export_fields=export_fields
    )


def _table_params(
    *,
    destination: EEExportDestination | str,
    name: str,
    collection: Any,
    asset_id: str | None = None,
    workspace_path: str | None = None,
    drive_folder: str | None = None,
    filename_prefix: str | None = None,
    file_format: str | None = "SHP",
    selectors: list[str] | None = None,
    max_vertices: int | None = None,
    strategy: str | None = None,
) -> dict[str, Any]:
    dest = _coerce_destination(destination)
    _require_asset_id(dest, asset_id)
    export_fields = _table_export_fields(
        collection=collection,
        asset_id=asset_id,
        workspace_path=workspace_path,
        drive_folder=drive_folder,
        filename_prefix=filename_prefix,
        file_format=file_format,
        selectors=selectors,
        max_vertices=max_vertices,
        strategy=strategy,
    )
    return _build_params(
        kind=EEExportKind.TABLE, destination=dest, name=name, export_fields=export_fields
    )


class EEExportsEndpoint:
    """Submit Earth Engine image/table exports through SEPAL TaskManager (sync)."""

    def __init__(self, tasks: TasksEndpoint) -> None:
        self._tasks = tasks

    def submit_image(
        self,
        *,
        image: Any,
        destination: EEExportDestination | str,
        name: str,
        region: Any = None,
        scale: float | None = None,
        crs: str | None = None,
        crs_transform: list[float] | None = None,
        dimensions: str | int | None = None,
        max_pixels: int | None = 10_000_000_000_000,
        shard_size: int | None = None,
        file_dimensions: int | list[int] | None = None,
        skip_empty_tiles: bool | None = None,
        file_format: str | None = "GEO_TIFF",
        format_options: dict[str, Any] | None = None,
        retries: int | None = None,
        asset_id: str | None = None,
        asset_type: str | None = None,
        sharing: str | None = None,
        strategy: str | None = None,
        pyramiding_policy: str | dict[str, str] | None = None,
        tile_size: int | None = None,
        properties: dict[str, Any] | None = None,
        workspace_path: str | None = None,
        drive_folder: str | None = None,
        filename_prefix: str | None = None,
        instance_type: str | None = None,
    ) -> Task:
        params = _image_params(
            destination=destination,
            name=name,
            image=image,
            region=region,
            scale=scale,
            crs=crs,
            crs_transform=crs_transform,
            dimensions=dimensions,
            max_pixels=max_pixels,
            shard_size=shard_size,
            file_dimensions=file_dimensions,
            skip_empty_tiles=skip_empty_tiles,
            file_format=file_format,
            format_options=format_options,
            retries=retries,
            asset_id=asset_id,
            asset_type=asset_type,
            sharing=sharing,
            strategy=strategy,
            pyramiding_policy=pyramiding_policy,
            tile_size=tile_size,
            properties=properties,
            workspace_path=workspace_path,
            drive_folder=drive_folder,
            filename_prefix=filename_prefix,
        )
        return self._tasks.submit("ee.export", params, instance_type=instance_type)

    def submit_table(
        self,
        *,
        collection: Any,
        destination: EEExportDestination | str,
        name: str,
        asset_id: str | None = None,
        workspace_path: str | None = None,
        drive_folder: str | None = None,
        filename_prefix: str | None = None,
        file_format: str | None = "SHP",
        selectors: list[str] | None = None,
        max_vertices: int | None = None,
        strategy: str | None = None,
        instance_type: str | None = None,
    ) -> Task:
        params = _table_params(
            destination=destination,
            name=name,
            collection=collection,
            asset_id=asset_id,
            workspace_path=workspace_path,
            drive_folder=drive_folder,
            filename_prefix=filename_prefix,
            file_format=file_format,
            selectors=selectors,
            max_vertices=max_vertices,
            strategy=strategy,
        )
        return self._tasks.submit("ee.export", params, instance_type=instance_type)
