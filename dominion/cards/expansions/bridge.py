from ..base_card import Card, CardCost, CardStats, CardType


class Bridge(Card):
    """Simplified implementation of the Bridge card."""

    def __init__(self):
        super().__init__(
            name="Bridge",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.cost_reduction = getattr(player, "cost_reduction", 0) + 1

