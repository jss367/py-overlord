import re
from typing import Type
from .base_way import Way
from .butterfly import WayOfTheButterfly
from .mouse import WayOfTheMouse

WAY_TYPES: dict[str, Type[Way]] = {
    "Way of the Butterfly": WayOfTheButterfly,
    "Way of the Mouse": WayOfTheMouse,
}


def get_way(name: str) -> Way:
    # Handle "Way of the Mouse (Card Name)" syntax
    match = re.match(r"^(Way of the Mouse)\s*\((.+)\)$", name)
    if match:
        card_name = match.group(2).strip()
        return WayOfTheMouse(set_aside_card_name=card_name)
    way_class = WAY_TYPES[name]
    return way_class()
