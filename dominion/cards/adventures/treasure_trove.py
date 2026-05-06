"""Treasure Trove (Adventures) — $5 Treasure."""

from ..base_card import Card, CardCost, CardStats, CardType


class TreasureTrove(Card):
    def __init__(self):
        super().__init__(
            name="Treasure Trove",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))
        if game_state.supply.get("Copper", 0) > 0:
            game_state.supply["Copper"] -= 1
            game_state.gain_card(player, get_card("Copper"))
