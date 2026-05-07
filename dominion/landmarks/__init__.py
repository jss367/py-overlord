from .base_landmark import Landmark
from .registry import LANDMARK_TYPES, get_all_landmark_names, get_landmark
from .wall import Wall

__all__ = [
    "Landmark",
    "LANDMARK_TYPES",
    "Wall",
    "get_all_landmark_names",
    "get_landmark",
]
