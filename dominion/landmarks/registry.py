"""Registry of Dominion landmarks."""

from typing import Type

from .base_landmark import Landmark
from .wall import Wall

LANDMARK_TYPES: dict[str, Type[Landmark]] = {
    "Wall": Wall,
}


def get_landmark(name: str) -> Landmark:
    """Return a fresh instance of the named landmark."""

    try:
        landmark_class = LANDMARK_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown landmark: {name}") from exc
    return landmark_class()


def get_all_landmark_names() -> list[str]:
    """Return the names of all registered landmarks."""
    return list(LANDMARK_TYPES.keys())
