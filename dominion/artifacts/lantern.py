"""Lantern artifact: holder's Border Guards reveal 3 cards, not 2."""

from __future__ import annotations

from .base_artifact import Artifact


class Lantern(Artifact):
    name = "Lantern"

    # Lantern is queried by Border Guard at play time via
    # ``state.artifacts.get("Lantern")``. There is no per-play hook; the
    # presence of this Artifact with the current player as holder is
    # checked directly when Border Guard resolves.
