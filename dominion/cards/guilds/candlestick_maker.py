from ..base_card import Card, CardCost, CardStats, CardType


class CandlestickMaker(Card):
    """Provides a Buy and a Coin token."""

    def __init__(self):
        super().__init__(
            name="Candlestick Maker",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.coin_tokens += 1
