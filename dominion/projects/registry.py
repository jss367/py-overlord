"""Registry of Dominion projects."""

from typing import Type

from .academy import Academy
from .barracks import Barracks
from .base_project import Project
from .capitalism import Capitalism
from .card_draw import CardDraw
from .cathedral import Cathedral
from .city_gate import CityGate
from .crop_rotation import CropRotation
from .exploration import Exploration
from .fair import Fair
from .fleet import Fleet
from .guildhall import Guildhall
from .innovation import Innovation
from .pageant import Pageant
from .piazza import Piazza
from .road_network import RoadNetwork
from .sewers import Sewers
from .silos import Silos
from .sinister_plot import SinisterPlot
from .star_chart import StarChart

PROJECT_TYPES: dict[str, Type[Project]] = {
    "Card Draw": CardDraw,
    "Sewers": Sewers,
    "Innovation": Innovation,
    "Road Network": RoadNetwork,
    "Cathedral": Cathedral,
    "City Gate": CityGate,
    "Pageant": Pageant,
    "Star Chart": StarChart,
    "Exploration": Exploration,
    "Fair": Fair,
    "Silos": Silos,
    "Sinister Plot": SinisterPlot,
    "Academy": Academy,
    "Capitalism": Capitalism,
    "Fleet": Fleet,
    "Guildhall": Guildhall,
    "Piazza": Piazza,
    "Barracks": Barracks,
    "Crop Rotation": CropRotation,
}


def get_project(name: str) -> Project:
    """Return a fresh instance of the named project."""

    try:
        project_class = PROJECT_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown project: {name}") from exc
    return project_class()
