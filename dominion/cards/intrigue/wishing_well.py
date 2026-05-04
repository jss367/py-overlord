"""Implementation of the Wishing Well card."""

from ..base_card import Card, CardCost, CardStats, CardType


class WishingWell(Card):
    def __init__(self):
        super().__init__(
            name="Wishing Well",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Step 1: Name the card BEFORE drawing/looking.
        guessed_name = player.ai.name_card_for_wishing_well(game_state, player)

        # Step 2: Reveal the top card of the deck.
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        card = player.deck.pop()

        if guessed_name and card.name == guessed_name:
            player.hand.append(card)
        else:
            player.deck.append(card)
