"""Star Chart: when you shuffle, you may pick one of the cards being
shuffled to put on top of your deck."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class StarChart(Project):
    def __init__(self) -> None:
        super().__init__("Star Chart", CardCost(coins=3))

    def on_shuffle(self, game_state, player):
        if not player.discard:
            return None
        candidates = [c for c in player.discard if game_state.is_action(c) or game_state.is_treasure(c)]
        if not candidates:
            return None
        best = max(
            candidates,
            key=lambda c: (game_state.is_action(c), c.cost.coins, c.stats.cards, c.name),
        )
        player.discard.remove(best)
        return best
