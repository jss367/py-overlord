from ..base_card import Card, CardCost, CardStats, CardType


class RootCellar(Card):
    """Action-Shadow ($3): +3 Cards, +1 Action, +3 Debt."""

    def __init__(self):
        super().__init__(
            name="Root Cellar",
            cost=CardCost(coins=3),
            stats=CardStats(cards=3, actions=1),
            types=[CardType.ACTION, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        game_state.current_player.debt += 3
