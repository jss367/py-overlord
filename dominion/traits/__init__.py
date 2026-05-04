"""Plunder Traits.

A Trait modifies the behaviour of a single Kingdom pile for the entire
game. Plunder ships 15 traits; the registry is wired into ``GameState`` at
setup time via :func:`apply_trait`.
"""

from .base_trait import Trait
from .registry import TRAITS, get_trait, apply_trait

__all__ = ["Trait", "TRAITS", "get_trait", "apply_trait"]
