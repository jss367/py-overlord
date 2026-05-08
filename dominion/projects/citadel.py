"""Citadel: the first Action you play each turn is replayed afterwards.

The replay itself is implemented inline in
``GameState.handle_action_phase`` (alongside Daimyo / Reckless / Rush /
Flagship). This module exists so Citadel can be registered as a Project
the player buys; the engine looks up the project by name on the player.
"""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Citadel(Project):
    def __init__(self) -> None:
        super().__init__("Citadel", CardCost(coins=8))
