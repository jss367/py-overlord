"""Figurine from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Figurine(Card):
    """$5 Action: +2 Cards, +1 Buy. You may discard an Action card for +1 Action."""

    def __init__(self):
        super().__init__(
            name="Figurine",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return

        choice = player.ai.choose_action(game_state, list(actions) + [None])
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        game_state.discard_card(player, choice)
        player.actions += 1
