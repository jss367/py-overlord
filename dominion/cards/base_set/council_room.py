from ..base_card import Card, CardCost, CardStats, CardType


class CouncilRoom(Card):
    """Base-set Council Room implementation."""

    def __init__(self):
        super().__init__(
            name="Council Room",
            cost=CardCost(coins=5),
            stats=CardStats(cards=4, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue
            game_state.draw_cards(other, 1)
