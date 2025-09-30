"""Implementation of the Destrier draw card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Destrier(Card):
    def __init__(self):
        super().__init__(
            name="Destrier",
            cost=CardCost(coins=6),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        return -getattr(player, "cards_gained_this_turn", 0)
