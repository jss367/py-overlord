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
        # "Your discard pile" refers to the active player's discard for
        # the duration of their turn, and the resulting cost applies
        # globally to every cost query during that turn (analogous to
        # Highway/Bridge). Compute the discount from the active turn
        # context, not from the `player` argument being queried, so
        # off-turn cost lookups see the same cost the active player sees.
        active = game_state.current_player
        if active is not None and not active.discard:
            return -3
        return 0
