"""Implementation of the Paddock horse gainer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Paddock(Card):
    def __init__(self):
        super().__init__(
            name="Paddock",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        try:
            horse = get_card("Horse")
        except ValueError:
            horse = None

        if horse is not None:
            game_state.gain_card(player, horse)

        player.actions += game_state.empty_piles
