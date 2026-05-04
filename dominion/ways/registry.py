import re
from typing import Type
from .base_way import Way
from .butterfly import WayOfTheButterfly
from .camel import WayOfTheCamel
from .chameleon import WayOfTheChameleon
from .frog import WayOfTheFrog
from .goat import WayOfTheGoat
from .horse import WayOfTheHorse
from .mole import WayOfTheMole
from .mouse import WayOfTheMouse
from .mule import WayOfTheMule
from .otter import WayOfTheOtter
from .owl import WayOfTheOwl
from .ox import WayOfTheOx
from .pig import WayOfThePig
from .rat import WayOfTheRat
from .sheep import WayOfTheSheep
from .squirrel import WayOfTheSquirrel
from .turtle import WayOfTheTurtle
from .worm import WayOfTheWorm

WAY_TYPES: dict[str, Type[Way]] = {
    "Way of the Butterfly": WayOfTheButterfly,
    "Way of the Camel": WayOfTheCamel,
    "Way of the Chameleon": WayOfTheChameleon,
    "Way of the Frog": WayOfTheFrog,
    "Way of the Goat": WayOfTheGoat,
    "Way of the Horse": WayOfTheHorse,
    "Way of the Mole": WayOfTheMole,
    "Way of the Mouse": WayOfTheMouse,
    "Way of the Mule": WayOfTheMule,
    "Way of the Otter": WayOfTheOtter,
    "Way of the Owl": WayOfTheOwl,
    "Way of the Ox": WayOfTheOx,
    "Way of the Pig": WayOfThePig,
    "Way of the Rat": WayOfTheRat,
    "Way of the Sheep": WayOfTheSheep,
    "Way of the Squirrel": WayOfTheSquirrel,
    "Way of the Turtle": WayOfTheTurtle,
    "Way of the Worm": WayOfTheWorm,
}


def get_way(name: str) -> Way:
    # Handle "Way of the Mouse (Card Name)" syntax
    match = re.match(r"^(Way of the Mouse)\s*\((.+)\)$", name)
    if match:
        card_name = match.group(2).strip()
        return WayOfTheMouse(set_aside_card_name=card_name)
    way_class = WAY_TYPES[name]
    return way_class()
