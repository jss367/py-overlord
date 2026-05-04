"""Livery - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Livery(Card):
    """+1 Action +$3. When you gain a card costing $4+, gain a Horse."""

    def __init__(self):
        super().__init__(
            name="Livery",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, coins=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # Track that there's a Livery in play; the gain hook handles the
        # Horse-grant trigger.
        pass
