"""Capitalism: during your turns, Action cards with +$ in their text are
also Treasures."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Capitalism(Project):
    def __init__(self) -> None:
        super().__init__("Capitalism", CardCost(coins=5))

    # GameState.is_treasure exposes the live type during the owner's turn,
    # so normal and indirect Treasure plays use the same bookkeeping.
