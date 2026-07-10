import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]


@nox.session(python=PYTHON_VERSIONS)
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


@nox.session(reuse_venv=True)
def docs(session: nox.Session) -> None:
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build", "--strict")


@nox.session(reuse_venv=True)
def docs_serve(session: nox.Session) -> None:
    session.install("-e", ".[docs]")
    session.run("mkdocs", "serve", *session.posargs)
