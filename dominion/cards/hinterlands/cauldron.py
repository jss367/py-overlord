from ..base_card import Card, CardCost, CardStats, CardType


class Cauldron(Card):
    """Hinterlands Treasure-Attack ($5).

    +$2, +1 Buy. The third time you gain an Action card on your
    turn, each other player gains a Curse.
    """

    def __init__(self):
        super().__init__(
            name="Cauldron",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE, CardType.ATTACK],
        )
