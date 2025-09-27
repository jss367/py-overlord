"""Registry of Dominion projects."""

from typing import Type

from .base_project import Project
from .card_draw import CardDraw
from .innovation import Innovation
from .sewers import Sewers

PROJECT_TYPES: dict[str, Type[Project]] = {
    "Card Draw": CardDraw,
    "Sewers": Sewers,
    "Innovation": Innovation,
}


def get_project(name: str) -> Project:
    """Return a fresh instance of the named project."""

    try:
        project_class = PROJECT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown project: {name}") from exc
    return project_class()

