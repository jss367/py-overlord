from ..base_card import Card, CardCost, CardStats, CardType


class Vault(Card):
    def __init__(self):
        super().__init__(
            name="Vault",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # TODO: discard for coins, others may discard for card
        pass
