"""Implementation of the Flagship action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Flagship(Card):
    def __init__(self):
        super().__init__(
            name="Flagship",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.flagship_pending = True
