from ..base_card import Card, CardCost, CardStats, CardType


class Litter(Card):
    """Action ($5): +2 Cards, +2 Actions, +1 Debt.

    The "+1 Debt" is taken when you play Litter (Debt-producing card text,
    similar to Imperial Envoy).
    """

    def __init__(self):
        super().__init__(
            name="Litter",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.debt += 1
