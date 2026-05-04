"""Sacred Grove — $5 Action.

+1 Buy +$3. Receive a Boon. If The Field's, Forest's, or River's, also
receive its bonus.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class SacredGrove(Card):
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Sacred Grove",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3, buys=1),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        # Boon is received via the Boons deck. Persistent Boons (Field's,
        # Forest's, River's) automatically also produce their bonus on
        # resolution — Sacred Grove just lets you receive any Boon as if
        # you were eligible. Implementation: receive the Boon as normal.
        player = game_state.current_player
        game_state.receive_boon(player)
