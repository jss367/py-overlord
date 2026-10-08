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
        self.duration_persistent = False
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        selected = []
        if player.hand:
            picks = player.ai.choose_gear_set_aside(
                game_state, player, list(player.hand)
            )
            for card in picks or []:
                index = next((i for i, held in enumerate(player.hand) if held is card), None)
                if index is not None:
                    selected.append(player.hand.pop(index))
                    if len(selected) == 2:
                        break
        # Replays add to this physical copy's storage instead of replacing it.
        self.set_aside.extend(selected)
        if selected:
            player.duration.append(self)
            self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []
        self.duration_persistent = False
