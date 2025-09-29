from ..base_card import Card, CardCost, CardStats, CardType


class WildHunt(Card):
    def __init__(self):
        super().__init__(
            name="Wild Hunt",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.vp_tokens += 1
