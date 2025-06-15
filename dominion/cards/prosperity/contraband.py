from ..base_card import Card, CardCost, CardStats, CardType


class Contraband(Card):
    def __init__(self):
        super().__init__(
            name="Contraband",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # TODO: implement buy restriction effect
        pass
