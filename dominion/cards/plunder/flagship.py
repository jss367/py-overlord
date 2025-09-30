"""Implementation of the Flagship action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Flagship(Card):
    def __init__(self):
        super().__init__(
            name="Flagship",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION, CardType.COMMAND],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.flagship_pending:
            player.flagship_pending.append(self)
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self.duration_persistent = self in player.flagship_pending
