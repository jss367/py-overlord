"""Ranger (Adventures) — $4 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Ranger(Card):
    def __init__(self):
        super().__init__(
            name="Ranger",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Flip the Journey token.
        player.journey_token_face_up = not player.journey_token_face_up
        if player.journey_token_face_up:
            game_state.draw_cards(player, 5)
