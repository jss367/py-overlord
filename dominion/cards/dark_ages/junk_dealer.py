"""Junk Dealer — $5 Action that cantrips and trashes a card."""

from ..base_card import Card, CardCost, CardStats, CardType


class JunkDealer(Card):
    """+1 Card +1 Action +$1. Trash a card from your hand."""

    def __init__(self):
        super().__init__(
            name="Junk Dealer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        choice = player.ai.choose_card_to_trash_with_junk_dealer(
            game_state, player, list(player.hand)
        )
        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
