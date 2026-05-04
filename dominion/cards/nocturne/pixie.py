"""Pixie — $2 Action.

+1 Action. Discard the top Boon and trash this; receive that Boon.
(Heirloom: Goat.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Pixie(Card):
    heirloom = "Goat"
    uses_boons = True
    nocturne_piles = {"Wish": 12}

    def __init__(self):
        super().__init__(
            name="Pixie",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        boon = game_state.draw_boon()
        if not boon:
            return
        if player.ai.should_play_pixie_for_boon(game_state, player, boon):
            # Trash Pixie, receive the Boon
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash_card(player, self)
            game_state.resolve_boon(player, boon)
        else:
            game_state.discard_boon(boon)
