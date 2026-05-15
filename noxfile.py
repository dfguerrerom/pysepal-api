import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]


@nox.session(python=PYTHON_VERSIONS, reuse_venv=True)
def tests(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("ruff", "check", "src", "tests")
    session.run("black", "--check", "src", "tests")


@nox.session(reuse_venv=True)
def mypy(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("mypy", "src/pysepal_api")
