from ..base_card import Card, CardCost, CardStats, CardType


class Talisman(Card):
    def __init__(self):
        super().__init__(
            name="Talisman",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def on_buy(self, game_state):
        # TODO: gain a copy of bought card costing 4 or less
        pass
