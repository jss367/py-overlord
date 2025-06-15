from ..base_card import Card, CardCost, CardStats, CardType


class Peddler(Card):
    def __init__(self):
        super().__init__(
            name="Peddler",
            cost=CardCost(coins=8),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        actions_in_play = sum(1 for c in player.in_play if c.is_action)
        return -2 * actions_in_play
