"""Jewelled Egg from the Plunder expansion."""

import random

from ..base_card import Card, CardCost, CardStats, CardType


class JewelledEgg(Card):
    """$2 Treasure: +$1, +1 Buy. When you trash this, +1 Coffer and gain 2 Loots."""

    def __init__(self):
        super().__init__(
            name="Jewelled Egg",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def on_trash(self, game_state, player):
        from ..registry import get_card
        from .loot_cards import LOOT_CARD_NAMES

        player.coin_tokens += 1
        for _ in range(2):
            loot_name = random.choice(LOOT_CARD_NAMES)
            loot = get_card(loot_name)
            game_state.gain_card(player, loot)
