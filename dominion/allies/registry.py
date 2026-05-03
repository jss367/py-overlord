"""Registry of Dominion Allies."""

from typing import Type

from .base_ally import Ally
from .cave_dwellers import CaveDwellers


ALLY_TYPES: dict[str, Type[Ally]] = {
    "Cave Dwellers": CaveDwellers,
}


def get_ally(name: str) -> Ally:
    try:
        ally_class = ALLY_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown ally: {name}") from exc
    return ally_class()
