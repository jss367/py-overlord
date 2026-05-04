"""Registry of Dominion Allies."""

from typing import Type

from .architects_guild import ArchitectsGuild
from .band_of_nomads import BandOfNomads
from .base_ally import Ally
from .cave_dwellers import CaveDwellers
from .circle_of_witches import CircleOfWitches
from .city_state import CityState
from .coastal_haven import CoastalHaven
from .crafters_guild import CraftersGuild
from .desert_guides import DesertGuides
from .family_of_inventors import FamilyOfInventors
from .fellowship_of_scribes import FellowshipOfScribes
from .forest_dwellers import ForestDwellers
from .gang_of_pickpockets import GangOfPickpockets
from .island_folk import IslandFolk
from .league_of_bankers import LeagueOfBankers
from .league_of_shopkeepers import LeagueOfShopkeepers
from .market_towns import MarketTowns
from .mountain_folk import MountainFolk
from .order_of_astrologers import OrderOfAstrologers
from .order_of_masons import OrderOfMasons
from .peaceful_cult import PeacefulCult
from .plateau_shepherds import PlateauShepherds
from .trappers_lodge import TrappersLodge
from .woodworkers_guild import WoodworkersGuild


ALLY_TYPES: dict[str, Type[Ally]] = {
    "Architects' Guild": ArchitectsGuild,
    "Band of Nomads": BandOfNomads,
    "Cave Dwellers": CaveDwellers,
    "Circle of Witches": CircleOfWitches,
    "City-state": CityState,
    "Coastal Haven": CoastalHaven,
    "Crafters' Guild": CraftersGuild,
    "Desert Guides": DesertGuides,
    "Family of Inventors": FamilyOfInventors,
    "Fellowship of Scribes": FellowshipOfScribes,
    "Forest Dwellers": ForestDwellers,
    "Gang of Pickpockets": GangOfPickpockets,
    "Island Folk": IslandFolk,
    "League of Bankers": LeagueOfBankers,
    "League of Shopkeepers": LeagueOfShopkeepers,
    "Market Towns": MarketTowns,
    "Mountain Folk": MountainFolk,
    "Order of Astrologers": OrderOfAstrologers,
    "Order of Masons": OrderOfMasons,
    "Peaceful Cult": PeacefulCult,
    "Plateau Shepherds": PlateauShepherds,
    "Trappers' Lodge": TrappersLodge,
    "Woodworkers' Guild": WoodworkersGuild,
}


def get_ally(name: str) -> Ally:
    try:
        ally_class = ALLY_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown ally: {name}") from exc
    return ally_class()
