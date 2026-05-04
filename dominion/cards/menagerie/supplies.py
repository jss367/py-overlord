"""Supplies - Treasure from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Supplies(Card):
    """$1. When you gain this, gain a Horse, putting it on top of your deck."""

    def __init__(self):
        super().__init__(
            name="Supplies",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        if game_state.supply.get("Horse", 0) <= 0:
            return
        game_state.supply["Horse"] -= 1
        game_state.gain_card(player, get_card("Horse"), to_deck=True)
