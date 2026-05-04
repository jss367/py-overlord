"""Hireling (Adventures) — $6 Action-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class Hireling(Card):
    def __init__(self):
        super().__init__(
            name="Hireling",
            cost=CardCost(coins=6),
            stats=CardStats(cards=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.hirelings_in_play += 1
        player.duration.append(self)

    def on_duration(self, game_state):
        # Stays in play forever; the +1 Card at start of turn is dispatched
        # by GameState (Hireling counts).
        self.duration_persistent = True
