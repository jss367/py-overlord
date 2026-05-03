"""Siren from the Plunder expansion."""

import random

from ..base_card import Card, CardCost, CardStats, CardType


class Siren(Card):
    """$3 Action: Trash an Action card from your hand. If you don't, trash this.
    Otherwise: +8 Cards, gain a Loot.
    """

    def __init__(self):
        super().__init__(
            name="Siren",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card
        from .loot_cards import LOOT_CARD_NAMES

        player = game_state.current_player

        actions_in_hand = [c for c in player.hand if c.is_action]
        chosen = None
        if actions_in_hand:
            chosen = player.ai.choose_card_to_trash(
                game_state, list(actions_in_hand) + [None]
            )
            if chosen not in actions_in_hand:
                chosen = None

        if chosen is None:
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash_card(player, self)
            return

        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        game_state.draw_cards(player, 8)

        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        game_state.gain_card(player, loot)
