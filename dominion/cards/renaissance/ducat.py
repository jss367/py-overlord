"""Ducat: Treasure ($2). $0. +1 Buy. +1 Coffers.

When you gain this, you may trash a Copper from your hand.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Ducat(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Ducat",
            cost=CardCost(coins=2),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        game_state.current_player.coin_tokens += 1

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        copper = next((c for c in player.hand if c.name == "Copper"), None)
        if copper is None:
            return
        player.hand.remove(copper)
        game_state.trash_card(player, copper)
