"""Crucible from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Crucible(Card):
    """$4 Treasure: +$1 per other Treasure you have in play."""

    def __init__(self):
        super().__init__(
            name="Crucible",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        other_treasures = sum(
            1 for c in player.in_play if c is not self and c.is_treasure
        )
        player.coins += other_treasures
