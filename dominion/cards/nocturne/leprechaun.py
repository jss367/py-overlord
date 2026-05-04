"""Leprechaun — $3 Action-Night.

Gain a Gold. If you have exactly 7 cards in play, gain a Wish; otherwise
receive a Hex.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Leprechaun(Card):
    nocturne_piles = {"Wish": 12}

    def __init__(self):
        super().__init__(
            name="Leprechaun",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DOOM],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))
        # Count cards in play AFTER gaining Gold (per official text uses
        # exactly 7 in play; we count current in_play including Leprechaun
        # itself, which mirrors the rule).
        if len(player.in_play) == 7:
            if game_state.supply.get("Wish", 0) > 0:
                game_state.supply["Wish"] -= 1
                game_state.gain_card(player, get_card("Wish"))
        else:
            game_state.give_hex_to_player(player)
