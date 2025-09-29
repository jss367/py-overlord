"""Registry of Dominion events."""

from typing import Type

from .base_event import Event
from .gain_silver import GainSilver
from .looting import Looting
from .menagerie_events import (
    Delay,
    Desperation,
    Enhance,
    Gamble,
    March,
    Ride,
    SeizeTheDay,
    Toil,
)

EVENT_TYPES: dict[str, Type[Event]] = {
    "Gain Silver": GainSilver,
    "Looting": Looting,
    "Desperation": Desperation,
    "Gamble": Gamble,
    "March": March,
    "Toil": Toil,
    "Enhance": Enhance,
    "Delay": Delay,
    "Ride": Ride,
    "Seize the Day": SeizeTheDay,
}


def get_event(name: str) -> Event:
    try:
        event_class = EVENT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown event: {name}") from exc
    return event_class()

