"""Changeling — $3 Action-Night.

Trash this. Gain a copy of a card you have in play. When you gain a card
costing $3+, you may exchange it for a Changeling.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Changeling(Card):
    def __init__(self):
        super().__init__(
            name="Changeling",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.trash_card(player, self)

        in_play_options = [c for c in player.in_play]
        if not in_play_options:
            return
        # Default: pick the most expensive in-play card available in supply.
        for card in sorted(in_play_options, key=lambda c: -c.cost.coins):
            if game_state.supply.get(card.name, 0) > 0:
                game_state.supply[card.name] -= 1
                from ..registry import get_card

                game_state.gain_card(player, get_card(card.name))
                return
