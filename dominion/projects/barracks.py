"""Barracks: at the start of your turn, +1 Action."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Barracks(Project):
    def __init__(self) -> None:
        super().__init__("Barracks", CardCost(coins=6))

    def on_turn_start(self, game_state, player) -> None:
        player.actions += 1
