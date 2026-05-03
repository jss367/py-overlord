"""Registry of Dominion events."""

from typing import Type

from .base_event import Event
from .continue_event import Continue
from .gain_silver import GainSilver
from .looting import Looting
from .menagerie_events import (
    Banish,
    Bargain,
    Delay,
    Desperation,
    Enhance,
    Gamble,
    Invest,
    March,
    Populate,
    Ride,
    SeizeTheDay,
    Stampede,
    Toil,
    Transport,
)
from .plunder_events import Avoid, Bury, Foray, Invasion, Peril, Prosper, Scrounge
from .prosperity_events import Investment
from .training import Training

EVENT_TYPES: dict[str, Type[Event]] = {
    "Gain Silver": GainSilver,
    "Looting": Looting,
    "Continue": Continue,
    "Desperation": Desperation,
    "Gamble": Gamble,
    "March": March,
    "Toil": Toil,
    "Enhance": Enhance,
    "Delay": Delay,
    "Ride": Ride,
    "Seize the Day": SeizeTheDay,
    "Banish": Banish,
    "Bargain": Bargain,
    "Invest": Invest,
    "Populate": Populate,
    "Stampede": Stampede,
    "Transport": Transport,
    "Investment": Investment,
    "Training": Training,
    "Bury": Bury,
    "Avoid": Avoid,
    "Foray": Foray,
    "Peril": Peril,
    "Scrounge": Scrounge,
    "Prosper": Prosper,
    "Invasion": Invasion,
}


def get_event(name: str) -> Event:
    try:
        event_class = EVENT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown event: {name}") from exc
    return event_class()

