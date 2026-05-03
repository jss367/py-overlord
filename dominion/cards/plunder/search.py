"""Search from the Plunder expansion."""

import random

from ..base_card import Card, CardCost, CardStats, CardType


class Search(Card):
    """$2 Action-Duration: +$1, +1 Buy. The next time you discard this from
    play, gain a Loot.
    """

    def __init__(self):
        super().__init__(
            name="Search",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        self.duration_persistent = False

    def on_discard_from_play(self, game_state, player):
        from ..registry import get_card
        from .loot_cards import LOOT_CARD_NAMES

        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        game_state.gain_card(player, loot)
