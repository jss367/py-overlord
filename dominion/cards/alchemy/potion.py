"""Potion - basic Treasure from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Potion(Card):
    """Treasure ($4): +1 Potion."""

    def __init__(self):
        super().__init__(
            name="Potion",
            cost=CardCost(coins=4),
            stats=CardStats(potions=1),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 16
