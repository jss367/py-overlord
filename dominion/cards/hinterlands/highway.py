from ..base_card import Card, CardCost, CardStats, CardType


class Highway(Card):
    def __init__(self):
        super().__init__(
            name="Highway",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.cost_reduction += 1
