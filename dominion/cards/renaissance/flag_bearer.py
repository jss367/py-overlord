"""Flag Bearer: Action ($4). +$2. +1 Buy.

When you gain or trash this, take the Flag artifact.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class FlagBearer(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Flag Bearer",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        game_state.take_artifact(player, "Flag")

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        game_state.take_artifact(player, "Flag")
