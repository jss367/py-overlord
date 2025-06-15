from ..base_card import Card, CardCost, CardStats, CardType


class SnowyVillage(Card):
    def __init__(self):
        super().__init__(
            name="Snowy Village",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=4),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.ignore_action_bonuses = True
