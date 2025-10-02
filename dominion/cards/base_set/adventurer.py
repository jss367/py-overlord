"""Implementation of the Adventurer treasure hunter."""

from ..base_card import Card, CardCost, CardStats, CardType


class Adventurer(Card):
    def __init__(self):
        super().__init__(
            name="Adventurer",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures_found = 0
        while treasures_found < 2:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()

            if not player.deck:
                break

            card = player.deck.pop()
            if card.is_treasure:
                player.hand.append(card)
                treasures_found += 1
            else:
                game_state.discard_card(player, card)
