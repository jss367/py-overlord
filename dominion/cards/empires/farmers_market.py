from ..base_card import Card, CardCost, CardStats, CardType


class FarmersMarket(Card):
    def __init__(self):
        super().__init__(
            name="Farmers' Market",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.vp_tokens += 1
