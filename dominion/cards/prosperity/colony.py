from ..base_card import Card, CardCost, CardStats, CardType


class Colony(Card):
    def __init__(self):
        super().__init__(
            name="Colony",
            cost=CardCost(coins=11),
            stats=CardStats(vp=10),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        return 12
