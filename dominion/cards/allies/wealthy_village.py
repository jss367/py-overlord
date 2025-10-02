"""Implementation of the Wealthy Village card."""

import random

from ..base_card import Card, CardCost, CardStats, CardType
from ..plunder import LOOT_CARD_NAMES


class WealthyVillage(Card):
    def __init__(self):
        super().__init__(
            name="Wealthy Village",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)
        treasures = {card.name for card in player.in_play if card.is_treasure}
        if len(treasures) < 3:
            return

        available = [
            name for name in LOOT_CARD_NAMES if game_state.supply.get(name, 0) > 0
        ]
        if not available:
            return

        loot_name = random.choice(available)
        loot = get_card(loot_name)
        game_state.gain_card(player, loot)
