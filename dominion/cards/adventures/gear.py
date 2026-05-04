"""Gear (Adventures) — $3 Action-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class Gear(Card):
    def __init__(self):
        super().__init__(
            name="Gear",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        self.set_aside = []
        if player.hand:
            picks = player.ai.choose_gear_set_aside(
                game_state, player, list(player.hand)
            )
            for card in picks[:2]:
                if card in player.hand:
                    player.hand.remove(card)
                    self.set_aside.append(card)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []
        self.duration_persistent = False
