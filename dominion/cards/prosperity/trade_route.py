from ..base_card import Card, CardCost, CardStats, CardType


class TradeRoute(Card):
    def __init__(self):
        super().__init__(
            name="Trade Route",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: gain coins equal to trade route mat and trash a card
        pass
