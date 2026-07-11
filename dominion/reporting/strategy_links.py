"""Shared links for generated strategy reports."""

from __future__ import annotations

import re


def strategy_slug(name: str) -> str:
    """Return a stable filename slug for a strategy display name."""

    slug = name.replace("-", " ").replace("_", " ").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "strategy"


def strategy_page_href(name: str, *, prefix: str = "strategies") -> str:
    """Return the conventional relative href for a strategy page."""

    return f"{prefix}/{strategy_slug(name)}.html"
