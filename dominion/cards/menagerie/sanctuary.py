"""Sanctuary - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sanctuary(Card):
    """+1 Card +1 Action +1 Buy. You may exile a card from your hand."""

    def __init__(self):
        super().__init__(
            name="Sanctuary",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_exile_for_sanctuary(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        player.exile.append(choice)
