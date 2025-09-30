"""Implementation of the Gardens victory card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Gardens(Card):
    """Simple victory card worth 1 VP per 10 cards owned."""

    def __init__(self):
        super().__init__(
            name="Gardens",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        total_cards = len(player.all_cards())
        return total_cards // 10
