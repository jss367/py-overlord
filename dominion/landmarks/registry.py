"""Registry of Empires Landmarks."""

import re
from typing import Type

from .base_landmark import Landmark
from .landmarks import (
    Aqueduct,
    Arena,
    BanditFort,
    Basilica,
    Baths,
    Battlefield,
    Colonnade,
    DefiledShrine,
    Fountain,
    Keep,
    Labyrinth,
    MountainPass,
    Museum,
    Obelisk,
    Orchard,
    Palace,
    Tomb,
    Tower,
    TriumphalArch,
    Wall,
    WolfDen,
)

LANDMARK_TYPES: dict[str, Type[Landmark]] = {
    "Aqueduct": Aqueduct,
    "Arena": Arena,
    "Bandit Fort": BanditFort,
    "Basilica": Basilica,
    "Baths": Baths,
    "Battlefield": Battlefield,
    "Colonnade": Colonnade,
    "Defiled Shrine": DefiledShrine,
    "Fountain": Fountain,
    "Keep": Keep,
    "Labyrinth": Labyrinth,
    "Mountain Pass": MountainPass,
    "Museum": Museum,
    "Obelisk": Obelisk,
    "Orchard": Orchard,
    "Palace": Palace,
    "Tomb": Tomb,
    "Tower": Tower,
    "Triumphal Arch": TriumphalArch,
    "Wall": Wall,
    "Wolf Den": WolfDen,
}

_PARAMETRIC_LANDMARK_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<target>.+)\)$")


def get_landmark(name: str) -> Landmark:
    match = _PARAMETRIC_LANDMARK_RE.fullmatch(name)
    if match:
        landmark_name = match.group("name").strip()
        target = match.group("target").strip()
        if landmark_name != "Obelisk":
            raise ValueError(f"Landmark does not support a chosen pile: {name}")
        return Obelisk(chosen_pile=target)

    try:
        cls = LANDMARK_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown landmark: {name}") from exc
    return cls()


def all_landmarks() -> list[Landmark]:
    """Return one fresh instance of each Landmark."""
    return [cls() for cls in LANDMARK_TYPES.values()]
