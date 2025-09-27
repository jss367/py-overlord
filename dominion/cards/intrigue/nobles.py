from ..base_card import Card, CardCost, CardStats, CardType


class Nobles(Card):
    """Intrigue Nobles implementation with simple choice logic."""

    def __init__(self):
        super().__init__(
            name="Nobles",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if player.actions <= 0:
            player.actions += 2
        else:
            game_state.draw_cards(player, 3)
