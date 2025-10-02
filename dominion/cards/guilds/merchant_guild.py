from ..base_card import Card, CardCost, CardStats, CardType


class MerchantGuild(Card):
    """Awards Coin tokens when cards are bought this turn."""

    def __init__(self):
        super().__init__(
            name="Merchant Guild",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.merchant_guilds_played += 1
