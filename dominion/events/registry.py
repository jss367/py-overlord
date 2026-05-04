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
from .plunder_events import (
    Avoid,
    Bury,
    Deliver,
    Foray,
    Invasion,
    Journey,
    Mirror,
    Peril,
    Prepare,
    Prosper,
    Scrounge,
)
from .prosperity_events import Investment
from .rising_sun_events import (
    Amass,
    Asceticism,
    Credit,
    Foresight,
    Gather,
    Kintsugi,
    Practice,
    ReceiveTribute,
    SeaTrade,
)
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
    # Plunder
    "Bury": Bury,
    "Avoid": Avoid,
    "Foray": Foray,
    "Peril": Peril,
    "Scrounge": Scrounge,
    "Prosper": Prosper,
    "Invasion": Invasion,
    "Mirror": Mirror,
    "Deliver": Deliver,
    "Prepare": Prepare,
    "Journey": Journey,
    # Rising Sun
    "Amass": Amass,
    "Asceticism": Asceticism,
    "Credit": Credit,
    "Foresight": Foresight,
    "Gather": Gather,
    "Kintsugi": Kintsugi,
    "Practice": Practice,
    "Receive Tribute": ReceiveTribute,
    "Sea Trade": SeaTrade,
}


def get_event(name: str) -> Event:
    try:
        event_class = EVENT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown event: {name}") from exc
    return event_class()

