"""Fair: at the start of your turn, +1 Buy."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Fair(Project):
    def __init__(self) -> None:
        super().__init__("Fair", CardCost(coins=4))

    def on_turn_start(self, game_state, player) -> None:
        player.buys += 1
