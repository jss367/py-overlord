"""Goatherd - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Goatherd(Card):
    """+1 Action +$1. You may trash a card from your hand. +$1 per other player
    to your left who has 5+ cards in hand.
    """

    def __init__(self):
        super().__init__(
            name="Goatherd",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Optional trash
        if player.hand:
            choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        # Count opponents with 5+ cards in hand
        count = sum(1 for p in game_state.players if p is not player and len(p.hand) >= 5)
        player.coins += count
