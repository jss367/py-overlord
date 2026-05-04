from .base_artifact import Artifact
from .flag import Flag
from .horn import Horn
from .key import Key
from .lantern import Lantern
from .treasure_chest import TreasureChest
from .registry import ARTIFACT_TYPES, get_artifact

__all__ = [
    "Artifact",
    "Flag",
    "Horn",
    "Key",
    "Lantern",
    "TreasureChest",
    "ARTIFACT_TYPES",
    "get_artifact",
]
