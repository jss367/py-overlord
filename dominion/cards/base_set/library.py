"""Implementation of the Library draw card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Library(Card):
    def __init__(self):
        super().__init__(
            name="Library",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        set_aside: list = []

        while len(player.hand) < 7:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break

            card = player.deck.pop()
            if card.is_action and player.actions <= 0:
                set_aside.append(card)
            else:
                player.hand.append(card)

        if set_aside:
            game_state.discard_cards(player, set_aside)
