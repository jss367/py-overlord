"""Implementation of Mining Village."""

from ..base_card import Card, CardCost, CardStats, CardType


class MiningVillage(Card):
    """+1 Card +2 Actions. You may trash this for +$2."""

    def __init__(self):
        super().__init__(
            name="Mining Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # The card has been moved from hand into player.in_play before
        # play_effect runs. Decide whether to trash it for +$2.
        if not self._should_self_trash(player):
            return

        # Find this exact instance in play and trash it.
        for idx in range(len(player.in_play) - 1, -1, -1):
            if player.in_play[idx] is self:
                player.in_play.pop(idx)
                game_state.trash_card(player, self)
                player.coins += 2
                return

    def _should_self_trash(self, player) -> bool:
        # Default: never self-trash. Mining Village is a Village body
        # that's normally more useful than a one-shot +$2; only specific
        # AIs/strategies should opt in by overriding this.
        return False
