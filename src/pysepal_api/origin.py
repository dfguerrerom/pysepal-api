"""Where an export comes from, so SEPAL's task list can name it.

SEPAL labels recipe exports with their project and recipe. Exports from this
client carry an ``origin`` instead, sent as ``taskInfo.origin``. A caller can
give one with the export; otherwise it is detected when the export is
submitted:

- ``{"type": "APP", "name": ...}`` named by the caller's ``app_name``, or by
  its ``module_name`` when it signs in with a browser session, as apps do. An
  app with neither sends its working directory as ``path``.
- ``{"type": "NOTEBOOK", "path": ...}`` from the notebook VS Code names in the
  kernel, or the one JupyterLab names in ``JPY_SESSION_NAME``.
- ``{"type": "SCRIPT", "path": ...}`` from the running script. A launcher
  installed with Python (``solara run app.py``, ``python -m tool``) is named by
  the ``.py`` file it was given.
- ``{"type": "SANDBOX", "path": ...}`` otherwise, with the working directory:
  a Python shell, ``python -c``, a console, or a kernel that names no notebook
  (Voila).

Paths are sent only from a SEPAL sandbox, those inside the SEPAL home relative
to it, like workspace paths. SEPAL shows a relative path as one in the SEPAL
home, so from elsewhere only the type is sent. A working directory that no
longer exists also leaves an origin without a path.
"""

from __future__ import annotations

import os
import site
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import TypeGuard

from .auth import SANDBOX_KEY_PATH
from .paths import BASE_REMOTE_PATH

ORIGIN_TYPES = ("NOTEBOOK", "SCRIPT", "APP", "SANDBOX")


def checked_origin(origin: Mapping[str, str]) -> dict[str, str]:
    """Return an origin a caller gave, as it will be sent; refuse an unknown type."""
    if origin.get("type") not in ORIGIN_TYPES:
        raise ValueError(
            f"origin type must be NOTEBOOK, SCRIPT, APP or SANDBOX, got {origin.get('type')!r}"
        )
    return dict(origin)


def detect_origin(
    *, app_name: str | None, module_name: str | None, browser_session: bool
) -> dict[str, str]:
    if app_name:
        return {"type": "APP", "name": app_name}
    if browser_session and module_name:
        return {"type": "APP", "name": module_name}
    origin_type, path = ("APP", _working_directory()) if browser_session else _running_code()
    if path is None or not os.path.exists(SANDBOX_KEY_PATH):
        return {"type": origin_type}
    return {"type": origin_type, "path": _home_relative(path)}


def _running_code() -> tuple[str, str | None]:
    main = sys.modules.get("__main__")
    # Inside a kernel, __main__ is the user namespace: it has no __file__, and holds the
    # globals VS Code injects.
    notebook = getattr(main, "__vsc_ipynb_file__", None)
    if _is_text(notebook):
        return "NOTEBOOK", notebook
    main_file = getattr(main, "__file__", None)
    if _is_text(main_file):
        script = _user_script(main_file)
        return ("SCRIPT", script) if script else ("SANDBOX", _working_directory())
    # Checked after __file__ because processes a notebook starts inherit it. Consoles are
    # named "Console N".
    session = os.environ.get("JPY_SESSION_NAME", "")
    if session.endswith(".ipynb"):
        return "NOTEBOOK", session
    return "SANDBOX", _working_directory()


# A launcher installed with Python (a console script, `python -m tool`) is not the user's code:
# the script it was given is.
def _user_script(main_file: str) -> str | None:
    if not _installed(main_file):
        return main_file
    for arg in sys.argv[1:]:
        if arg.endswith(".py") and os.path.isfile(arg):
            return os.path.abspath(arg)
    return None


def _installed(path: str) -> bool:
    file = Path(path).resolve()
    prefixes = {sys.prefix, sys.base_prefix, site.getuserbase()}
    return any(file.is_relative_to(Path(prefix).resolve()) for prefix in prefixes)


def _working_directory() -> str | None:
    try:
        return os.getcwd()
    except OSError:
        return None


def _home_relative(path: str) -> str:
    home = PurePosixPath(BASE_REMOTE_PATH)
    candidate = PurePosixPath(path)
    return str(candidate.relative_to(home)) if candidate.is_relative_to(home) else path


def _is_text(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and value != ""
