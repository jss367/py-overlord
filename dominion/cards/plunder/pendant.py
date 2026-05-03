"""Pendant from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Pendant(Card):
    """$5 Treasure: +$1 per Action card you have in play."""

    def __init__(self):
        super().__init__(
            name="Pendant",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        action_count = sum(1 for c in player.in_play if c.is_action)
        player.coins += action_count
