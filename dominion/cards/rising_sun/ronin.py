from ..base_card import Card, CardCost, CardStats, CardType


class Ronin(Card):
    """Action-Shadow ($5):
    Draw cards one at a time until you have 7 cards in hand (or can't draw
    any more); if you already had 7 or more cards in hand, you don't draw
    any.
    """

    def __init__(self):
        super().__init__(
            name="Ronin",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if len(player.hand) >= 7:
            return

        while len(player.hand) < 7:
            drawn = player.draw_cards(1)
            if not drawn:
                break
