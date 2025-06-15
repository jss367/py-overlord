from ..base_card import Card, CardCost, CardStats, CardType


class Goons(Card):
    def __init__(self):
        super().__init__(
            name="Goons",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        # TODO: force others to discard to 3 and award VP tokens per buy
        pass
