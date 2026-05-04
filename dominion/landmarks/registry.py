"""Registry of Empires Landmarks."""

from typing import Type

from .base_landmark import Landmark
from .landmarks import (
    Aqueduct,
    Arena,
    BanditFort,
    Basilica,
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


def get_landmark(name: str) -> Landmark:
    try:
        cls = LANDMARK_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown landmark: {name}") from exc
    return cls()


def all_landmarks() -> list[Landmark]:
    """Return one fresh instance of each Landmark."""
    return [cls() for cls in LANDMARK_TYPES.values()]
