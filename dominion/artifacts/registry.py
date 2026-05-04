"""Registry of Renaissance Artifacts."""

from __future__ import annotations

from typing import Type

from .base_artifact import Artifact
from .flag import Flag
from .horn import Horn
from .key import Key
from .lantern import Lantern
from .treasure_chest import TreasureChest

ARTIFACT_TYPES: dict[str, Type[Artifact]] = {
    "Flag": Flag,
    "Horn": Horn,
    "Key": Key,
    "Lantern": Lantern,
    "Treasure Chest": TreasureChest,
}


def get_artifact(name: str) -> Artifact:
    """Return a fresh instance of the named artifact."""

    try:
        cls = ARTIFACT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown artifact: {name}") from exc
    return cls()
