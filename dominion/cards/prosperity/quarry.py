from ..base_card import Card, CardCost, CardStats, CardType


class Quarry(Card):
    def __init__(self):
        super().__init__(
            name="Quarry",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # Cost reduction is applied in GameState.get_card_cost while this card is in play
        pass
