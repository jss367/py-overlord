from ..base_card import Card, CardCost, CardStats, CardType


class Groundskeeper(Card):
    def __init__(self):
        super().__init__(
            name="Groundskeeper",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.groundskeeper_bonus = getattr(player, "groundskeeper_bonus", 0) + 1
