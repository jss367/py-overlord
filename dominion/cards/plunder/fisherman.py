"""Fisherman - Action from Plunder."""

from ..base_card import Card, CardCost, CardStats, CardType


class Fisherman(Card):
    """+1 Card, +1 Action, +$1.

    While your discard pile is empty, this costs $2.
    """

    def __init__(self):
        super().__init__(
            name="Fisherman",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        if not player.discard:
            return -3
        return 0
