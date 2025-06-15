from ..base_card import Card, CardCost, CardStats, CardType


class Platinum(Card):
    def __init__(self):
        super().__init__(
            name="Platinum",
            cost=CardCost(coins=9),
            stats=CardStats(coins=5),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 12
