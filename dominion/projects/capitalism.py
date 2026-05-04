"""Capitalism: during your turns, Action cards with +$ in their text are
also Treasures."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Capitalism(Project):
    def __init__(self) -> None:
        super().__init__("Capitalism", CardCost(coins=5))

    # The actual handling is in ``GameState.handle_treasure_phase`` which
    # checks ``player.projects`` for a Capitalism instance and lets the
    # player play Action cards with stats.coins > 0 during the treasure
    # phase. Nothing further needed here.
