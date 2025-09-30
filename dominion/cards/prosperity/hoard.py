from ..base_card import Card, CardCost, CardStats, CardType


class Hoard(Card):
    def __init__(self):
        super().__init__(
            name="Hoard",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def on_buy(self, game_state):
        """Hoard's bonus is handled while resolving purchases in GameState."""
        pass
