from ..base_card import Card, CardCost, CardStats, CardType


class Wharf(Card):
    """Simplified Wharf that draws cards and gives extra buys this and next turn."""

    def __init__(self) -> None:
        super().__init__(
            name="Wharf",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        # Add to duration pile so on_duration triggers next turn
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.buys += 1

