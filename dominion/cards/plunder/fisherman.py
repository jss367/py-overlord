"""Fisherman - Action from Plunder."""

from ..base_card import Card, CardCost, CardStats, CardType


class Fisherman(Card):
    """+1 Card, +1 Action, +$1.

    During your turns, this costs $1 less while your discard pile is empty.
    """

    def __init__(self):
        super().__init__(
            name="Fisherman",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        if game_state.current_player is player and not player.discard:
            return -1
        return 0
