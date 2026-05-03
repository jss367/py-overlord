"""Sack of Loot from the Plunder expansion."""

import random

from ..base_card import Card, CardCost, CardStats, CardType


class SackOfLoot(Card):
    """$6 Treasure: +$1, +1 Buy, gain a Loot."""

    def __init__(self):
        super().__init__(
            name="Sack of Loot",
            cost=CardCost(coins=6),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        from ..registry import get_card
        from .loot_cards import LOOT_CARD_NAMES

        player = game_state.current_player
        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        game_state.gain_card(player, loot)
