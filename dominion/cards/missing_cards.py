from .base_card import Card, CardCost, CardStats, CardType


class Trail(Card):
    def __init__(self):
        super().__init__(
            name="Trail",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )


class ActingTroupe(Card):
    def __init__(self):
        super().__init__(
            name="Acting Troupe",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )


class Taskmaster(Card):
    def __init__(self):
        super().__init__(
            name="Taskmaster",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.DURATION],
        )


class Trader(Card):
    def __init__(self):
        super().__init__(
            name="Trader",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )


class Torturer(Card):
    def __init__(self):
        super().__init__(
            name="Torturer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )


class Patrol(Card):
    def __init__(self):
        super().__init__(
            name="Patrol",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )


class Inn(Card):
    def __init__(self):
        super().__init__(
            name="Inn",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=2),
            types=[CardType.ACTION],
        )


class FirstMate(Card):
    def __init__(self):
        super().__init__(
            name="First Mate",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )
