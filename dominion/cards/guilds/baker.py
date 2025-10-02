from ..base_card import Card, CardCost, CardStats, CardType


class Baker(Card):
    """Cantrip that hands out a Coin token on play."""

    def __init__(self):
        super().__init__(
            name="Baker",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.coin_tokens += 1
