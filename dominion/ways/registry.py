from typing import Type
from .base_way import Way
from .butterfly import WayOfTheButterfly

WAY_TYPES: dict[str, Type[Way]] = {
    "Way of the Butterfly": WayOfTheButterfly,
}


def get_way(name: str) -> Way:
    way_class = WAY_TYPES[name]
    return way_class()
