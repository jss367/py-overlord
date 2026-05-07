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
        # The discount is turn-scoped: only the player whose turn it is
        # sees Fisherman drop to $2 when their discard is empty. Off-turn
        # cost queries (e.g. Changeling's $3+ exchange trigger when a
        # card is gained on another player's turn) must see the printed
        # cost.
        if game_state.current_player is player and not player.discard:
            return -3
        return 0
