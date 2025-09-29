from ..base_card import Card, CardCost, CardStats, CardType


class Tunnel(Card):
    def __init__(self):
        super().__init__(
            name="Tunnel",
            cost=CardCost(coins=3),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY, CardType.REACTION],
        )
