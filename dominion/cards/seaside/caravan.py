from ..base_card import Card, CardCost, CardStats, CardType


class Caravan(Card):
    """Action-Duration ($4): +1 Card, +1 Action. At the start of your next turn:
    +1 Card.
    """

    def __init__(self):
        super().__init__(
            name="Caravan",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self.duration_persistent = False
