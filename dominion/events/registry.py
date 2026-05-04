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
from .empires_events import (
    Advance,
    Annex,
    Banquet,
    Conquest,
    Delve,
    Dominate,
    Donate,
    Ritual,
    SaltTheEarth,
    Tax,
    Triumph,
    Wedding,
    Windfall,
)

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
    # Empires
    "Triumph": Triumph,
    "Annex": Annex,
    "Donate": Donate,
    "Advance": Advance,
    "Delve": Delve,
    "Tax": Tax,
    "Banquet": Banquet,
    "Ritual": Ritual,
    "Salt the Earth": SaltTheEarth,
    "Wedding": Wedding,
    "Windfall": Windfall,
    "Conquest": Conquest,
    "Dominate": Dominate,
}


def get_event(name: str) -> Event:
    try:
        event_class = EVENT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown event: {name}") from exc
    return event_class()

