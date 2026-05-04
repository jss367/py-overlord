"""Shepherd — $4 Action.

+1 Action. Discard any number of Victory cards. +2 Cards per card discarded.
(Heirloom: Pasture.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Shepherd(Card):
    heirloom = "Pasture"

    def __init__(self):
        super().__init__(
            name="Shepherd",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        victories = [c for c in player.hand if c.is_victory]
        if not victories:
            return
        chosen = player.ai.choose_shepherd_discards(game_state, player, victories)
        actually = 0
        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                actually += 1
        if actually:
            game_state.draw_cards(player, actually * 2)
