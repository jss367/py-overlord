"""Abundance from the Plunder expansion."""

import random

from ..base_card import Card, CardCost, CardStats, CardType


class Abundance(Card):
    """$4 Action-Duration: +1 Buy. At start of next turn, +1 Buy. If you played
    no Treasure cards this turn, gain a Loot.
    """

    def __init__(self):
        super().__init__(
            name="Abundance",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card
        from .loot_cards import LOOT_CARD_NAMES

        player = game_state.current_player
        player.buys += 1

        treasures_in_play = any(c.is_treasure for c in player.in_play)
        if not treasures_in_play:
            loot_name = random.choice(LOOT_CARD_NAMES)
            loot = get_card(loot_name)
            game_state.gain_card(player, loot)

        self.duration_persistent = False
