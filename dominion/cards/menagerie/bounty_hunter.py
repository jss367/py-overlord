"""Bounty Hunter - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class BountyHunter(Card):
    """+1 Action. Exile a card from your hand. +$3 if you didn't have a copy
    of it in Exile.
    """

    def __init__(self):
        super().__init__(
            name="Bounty Hunter",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        # Pick a card to exile - prefer a useless card the AI would trash.
        choice = player.ai.choose_card_to_exile_for_bounty_hunter(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            return

        already_exiled = any(c.name == choice.name for c in player.exile)
        player.hand.remove(choice)
        player.exile.append(choice)

        if not already_exiled:
            player.coins += 3
