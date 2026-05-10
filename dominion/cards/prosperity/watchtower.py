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
        """Draw until the current player has six cards in hand.

        Stops if the deck and discard are both exhausted — otherwise a
        thinned-out player could loop forever while ``draw_cards`` returns
        nothing but the hand never reaches six.
        """

        player = game_state.current_player
        while len(player.hand) < 6:
            drawn = game_state.draw_cards(player, 1)
            if not drawn:
                break
