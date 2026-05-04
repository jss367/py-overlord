"""Scholar: Action ($5). Discard your hand. +7 Cards."""

from ..base_card import Card, CardCost, CardStats, CardType


class Scholar(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Scholar",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        hand = list(player.hand)
        player.hand = []
        for card in hand:
            game_state.discard_card(player, card)
        game_state.draw_cards(player, 7)
