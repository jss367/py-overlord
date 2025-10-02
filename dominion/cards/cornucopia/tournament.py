from ..base_card import Card, CardCost, CardStats, CardType


class Tournament(Card):
    """Provides a light mix of cards and actions for simulation purposes."""

    def __init__(self):
        super().__init__(
            name="Tournament",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.coins += 1
