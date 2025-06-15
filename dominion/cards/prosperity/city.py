from ..base_card import Card, CardCost, CardStats, CardType


class City(Card):
    def __init__(self):
        super().__init__(
            name="City",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: add bonuses for empty piles
        pass
