"""Canal: during your turns, all cards cost $1 less (but not less than $0)."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Canal(Project):
    def __init__(self) -> None:
        super().__init__("Canal", CardCost(coins=7))

    def on_buy(self, game_state, player) -> None:
        # The discount is "during your turns" — continuous from the
        # moment Canal is bought. Apply immediately so any further buys
        # this same turn benefit; on_turn_start re-applies on later turns.
        player.cost_reduction += 1

    def on_turn_start(self, game_state, player) -> None:
        player.cost_reduction += 1
