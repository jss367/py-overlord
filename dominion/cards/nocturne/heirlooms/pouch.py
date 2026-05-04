"""Pouch — Tracker's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class Pouch(Card):
    """$1 Treasure-Heirloom: +1 Buy."""

    def __init__(self):
        super().__init__(
            name="Pouch",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0
