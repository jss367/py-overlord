"""Pasture — Shepherd's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class Pasture(Card):
    """$2 Treasure-Victory-Heirloom: $1. Worth 1 VP per Estate."""

    def __init__(self):
        super().__init__(
            name="Pasture",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.VICTORY, CardType.HEIRLOOM],
        )

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

    def get_victory_points(self, player) -> int:
        return sum(1 for c in player.all_cards() if c.name == "Estate")
