"""Blessed Village — $4 Action.

+1 Card +2 Actions. When you gain this, receive a Boon now or at start of
next turn (default: now).
"""

from ..base_card import Card, CardCost, CardStats, CardType


class BlessedVillage(Card):
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Blessed Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION, CardType.FATE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # Default: receive the Boon immediately.
        game_state.receive_boon(player)
