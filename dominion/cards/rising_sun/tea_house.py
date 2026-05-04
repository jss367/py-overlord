from ..base_card import Card, CardCost, CardStats, CardType


class TeaHouse(Card):
    """Action-Omen ($5): +1 Sun, +1 Card, +1 Action, +$2."""

    def __init__(self):
        super().__init__(
            name="Tea House",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=2),
            types=[CardType.ACTION, CardType.OMEN],
        )
