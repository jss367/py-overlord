from ..base_card import Card, CardCost, CardStats, CardType


class Watchtower(Card):
    def __init__(self):
        super().__init__(
            name="Watchtower",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        while len(player.hand) < 6:
            game_state.draw_cards(player, 1)
