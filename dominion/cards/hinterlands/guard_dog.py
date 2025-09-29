from ..base_card import Card, CardCost, CardStats, CardType


class GuardDog(Card):
    def __init__(self):
        super().__init__(
            name="Guard Dog",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.hand) <= 5:
            game_state.draw_cards(player, 2)
