from ..base_card import Card, CardCost, CardStats, CardType


class Talisman(Card):
    def __init__(self):
        super().__init__(
            name="Talisman",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def on_buy(self, game_state):
        """Extra gains from Talisman are handled during the buy phase."""
        pass
