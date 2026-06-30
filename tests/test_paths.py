from pathlib import PurePosixPath

import pytest

from pysepal_api.paths import (
    BASE_REMOTE_PATH,
    normalize_list_folder,
    sanitize_write_path,
)


def test_base_remote_path() -> None:
    assert BASE_REMOTE_PATH == "/home/sepal-user"


def test_sanitize_strips_home_prefix() -> None:
    p = sanitize_write_path("/home/sepal-user/module_results/app/out.csv")
    assert p == PurePosixPath("module_results/app/out.csv")


def test_sanitize_passes_relative_through() -> None:
    assert sanitize_write_path("module_results/app/out.csv") == PurePosixPath(
        "module_results/app/out.csv"
    )


def test_sanitize_rejects_outside_home() -> None:
    with pytest.raises(ValueError):
        sanitize_write_path("/etc/passwd")


def test_sanitize_rejects_traversal_absolute() -> None:
    with pytest.raises(ValueError):
        sanitize_write_path("/home/sepal-user/../../etc/passwd")


def test_sanitize_rejects_traversal_relative() -> None:
    with pytest.raises(ValueError):
        sanitize_write_path("../outside")


def test_normalize_list_folder_root_to_dot() -> None:
    assert normalize_list_folder("/") == "."


def test_normalize_list_folder_keeps_relative() -> None:
    assert normalize_list_folder("module_results/app") == "module_results/app"


def test_normalize_list_folder_strips_home() -> None:
    assert normalize_list_folder("/home/sepal-user/module_results/app") == ("module_results/app")


def test_normalize_list_folder_rejects_relative_traversal() -> None:
    with pytest.raises(ValueError):
        normalize_list_folder("../../etc")


def test_normalize_list_folder_rejects_absolute_traversal() -> None:
    with pytest.raises(ValueError):
        normalize_list_folder("/home/sepal-user/../../etc")


def test_path_errors_are_pysepal_and_value_errors() -> None:
    from pysepal_api.errors import InvalidPathError, PysepalError

    for bad in ("../escape", "/etc/passwd"):
        with pytest.raises(InvalidPathError):
            sanitize_write_path(bad)
        # contract: catchable via the library root AND still a ValueError
        with pytest.raises(PysepalError):
            sanitize_write_path(bad)
        with pytest.raises(ValueError):
            sanitize_write_path(bad)
    with pytest.raises(PysepalError):
        normalize_list_folder("../../etc")
