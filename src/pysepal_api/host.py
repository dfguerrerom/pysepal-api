"""Resolve and normalize the SEPAL base URL.

Precedence (highest first):

1. Explicit `base_url=` (handled by the caller; a bare host is accepted).
2. `SEPAL_ENDPOINT` env var, treated as a full URL.
3. `SEPAL_HOST` env var, treated as a bare host.
"""

from __future__ import annotations

import os

from .errors import MissingHostError


def normalize_base_url(value: str) -> str:
    """Accept a bare host or full URL; return a full URL without trailing slash."""
    v = value.strip().rstrip("/")
    if "://" in v:
        return v
    return f"https://{v}"


def detect_base_url() -> str:
    endpoint = os.getenv("SEPAL_ENDPOINT")
    if endpoint:
        return normalize_base_url(endpoint)
    host = os.getenv("SEPAL_HOST")
    if host:
        return normalize_base_url(host)
    raise MissingHostError(
        "No SEPAL host configured. Pass base_url=..., set SEPAL_HOST, " "or set SEPAL_ENDPOINT."
    )
