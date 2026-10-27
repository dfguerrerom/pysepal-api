"""Where an export comes from, so SEPAL's task list can name it.

SEPAL labels recipe exports with their project and recipe. Exports from this
client carry an ``origin`` instead, sent as ``taskInfo.origin``:

- ``{"type": "APP", "name": ...}`` named by the caller's ``app_name``, or by
  its ``module_name`` when it signs in with a browser session, as apps do. An
  app with neither sends its working directory as ``path``.
- ``{"type": "NOTEBOOK", "path": ...}`` from the path JupyterLab gives the
  kernel in ``JPY_SESSION_NAME``, or the global VS Code injects.
- ``{"type": "SCRIPT", "path": ...}`` from the running script.
- ``{"type": "SANDBOX", "path": ...}`` otherwise, with the working directory:
  a Python shell, ``python -c``, or a kernel that names no notebook (Voila).

Paths inside the home directory are sent relative to it, like workspace paths.
Only a working directory that no longer exists leaves an origin without a path.
"""

from __future__ import annotations

import os
import sys
from pathlib import PurePosixPath


def detect_origin(
    *, app_name: str | None, module_name: str | None, browser_session: bool
) -> dict[str, str]:
    if app_name:
        return {"type": "APP", "name": app_name}
    if browser_session:
        if module_name:
            return {"type": "APP", "name": module_name}
        return _in_working_directory("APP")
    main = sys.modules.get("__main__")
    # Inside a kernel, __main__ is the user namespace: it has no __file__, and
    # holds the globals VS Code injects.
    notebook = os.environ.get("JPY_SESSION_NAME") or getattr(main, "__vsc_ipynb_file__", None)
    if isinstance(notebook, str) and notebook:
        return {"type": "NOTEBOOK", "path": _home_relative(notebook)}
    script = getattr(main, "__file__", None)
    if isinstance(script, str) and script:
        return {"type": "SCRIPT", "path": _home_relative(script)}
    return _in_working_directory("SANDBOX")


def _in_working_directory(origin_type: str) -> dict[str, str]:
    try:
        cwd = os.getcwd()
    except OSError:
        return {"type": origin_type}
    return {"type": origin_type, "path": _home_relative(cwd)}


def _home_relative(path: str) -> str:
    home = PurePosixPath(os.path.expanduser("~"))
    candidate = PurePosixPath(path)
    if candidate.is_relative_to(home):
        return str(candidate.relative_to(home))
    return path
