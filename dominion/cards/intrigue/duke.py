"""Implementation of Duke."""

from ..base_card import Card, CardCost, CardStats, CardType


class Duke(Card):
    """Worth 1 VP per Duchy you have."""

    def __init__(self):
        super().__init__(
            name="Duke",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        return sum(1 for card in player.all_cards() if card.name == "Duchy")
