"""Implementation of the Merchant card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Merchant(Card):
    """Action ($3): +1 Card, +1 Action.

    The first time you play a Silver this turn, +$1.
    """

    def __init__(self):
        super().__init__(
            name="Merchant",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # Each Merchant played gives +1 to the merchant_silver_bonus counter.
        # When the player plays their first Silver this turn the treasure
        # phase resolution adds the accumulated bonus and resets it.
        player = game_state.current_player
        player.merchant_silver_bonus = getattr(player, "merchant_silver_bonus", 0) + 1
