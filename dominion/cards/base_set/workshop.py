from ..base_card import Card, CardCost, CardStats, CardType


class Workshop(Card):
    def __init__(self):
        super().__init__(
            name="Workshop",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Gain a card costing up to 4 coins."""
        player = game_state.current_player

        from ..gain_decisions import choose_free_gain, gain_menu, gain_selected

        choices = gain_menu(game_state, player, CardCost(coins=4))
        gain_selected(game_state, player, choose_free_gain(
            game_state, player, choices, "Workshop"
        ), choices=choices, source="Workshop")
