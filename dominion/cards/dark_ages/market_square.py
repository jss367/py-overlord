from ..base_card import Card, CardCost, CardStats, CardType


class MarketSquare(Card):
    """+1 Card, +1 Action, +1 Buy.

    When you trash a card, you may discard this from your hand. If you do,
    gain a Gold.
    """

    def __init__(self):
        super().__init__(
            name="Market Square",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1, buys=1),
            types=[CardType.ACTION, CardType.REACTION],
        )
