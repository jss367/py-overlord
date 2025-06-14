from ..base_card import Card, CardCost, CardStats, CardType


class Collection(Card):
    def __init__(self):
        super().__init__(
            name="Collection",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        game_state.current_player.collection_played += 1
