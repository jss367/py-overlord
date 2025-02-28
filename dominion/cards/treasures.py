from .base_card import Card, CardCost, CardStats, CardType


class Copper(Card):
    def __init__(self):
        super().__init__(
            name="Copper",
            cost=CardCost(coins=0),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 60


class Silver(Card):
    def __init__(self):
        super().__init__(
            name="Silver",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 40


class Gold(Card):
    def __init__(self):
        super().__init__(
            name="Gold",
            cost=CardCost(coins=6),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def starting_supply(self, game_state) -> int:
        return 30
