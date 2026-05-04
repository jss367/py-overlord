"""Storeroom — $3 Action that turns junk in hand into cards then coin."""

from ..base_card import Card, CardCost, CardStats, CardType


class Storeroom(Card):
    """+1 Buy. Discard any number of cards, +1 Card per card discarded.

    Then discard any number of cards again, +$1 per card discarded the second
    time.
    """

    def __init__(self):
        super().__init__(
            name="Storeroom",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        first = player.ai.choose_storeroom_first_discards(
            game_state, player, list(player.hand)
        )
        first_count = 0
        for card in first:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                first_count += 1
        if first_count > 0:
            game_state.draw_cards(player, first_count)

        second = player.ai.choose_storeroom_second_discards(
            game_state, player, list(player.hand)
        )
        second_count = 0
        for card in second:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                second_count += 1
        player.coins += second_count
