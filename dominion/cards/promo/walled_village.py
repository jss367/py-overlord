from ..base_card import Card, CardCost, CardStats, CardType


class WalledVillage(Card):
    """Village that can topdeck itself when it's your only copy."""

    def __init__(self):
        super().__init__(
            name="Walled Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.walled_villages_played += 1
