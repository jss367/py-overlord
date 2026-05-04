"""Implementation of Great Hall (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class GreatHall(Card):
    """+1 Card +1 Action. Worth 1 VP."""

    def __init__(self):
        super().__init__(
            name="Great Hall",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1, vp=1),
            types=[CardType.ACTION, CardType.VICTORY],
        )
