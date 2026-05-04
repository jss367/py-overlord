"""Registry of Rising Sun Prophecies."""

from typing import Type

from .base_prophecy import Prophecy

PROPHECY_TYPES: dict[str, Type[Prophecy]] = {}


def register(cls: Type[Prophecy]) -> Type[Prophecy]:
    """Decorator to register a Prophecy subclass by its instance ``name``."""
    instance = cls()
    PROPHECY_TYPES[instance.name] = cls
    return cls


def get_prophecy(name: str) -> Prophecy:
    try:
        prophecy_class = PROPHECY_TYPES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown prophecy: {name}") from exc
    return prophecy_class()
