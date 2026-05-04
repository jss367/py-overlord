"""Pooka — $5 Action.

You may trash a non-Cursed-Gold Treasure from hand for +4 Cards.
(Heirloom: Cursed Gold.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Pooka(Card):
    heirloom = "Cursed Gold"

    def __init__(self):
        super().__init__(
            name="Pooka",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures = [
            c for c in player.hand
            if c.is_treasure and c.name != "Cursed Gold"
        ]
        if not treasures:
            return
        chosen = player.ai.should_pooka_trash_treasure(game_state, player, treasures)
        if chosen is None or chosen not in player.hand:
            return
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)
        game_state.draw_cards(player, 4)
