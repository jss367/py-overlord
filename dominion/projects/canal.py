"""Canal: during your turns, all cards cost $1 less (but not less than $0)."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Canal(Project):
    def __init__(self) -> None:
        super().__init__("Canal", CardCost(coins=7))

    def on_turn_start(self, game_state, player) -> None:
        player.cost_reduction += 1
