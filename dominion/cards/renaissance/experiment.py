"""Experiment: Action ($3). +2 Cards. +1 Action. Return this to its pile.

When you gain this, also gain another Experiment (which is not returned
to the pile when its on-gain rule fires — only the played-then-return
copy goes back).
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Experiment(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Experiment",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )
        # Track whether this copy is the freebie, which doesn't trigger
        # another freebie on gain. Set by the play handler before gain.
        self._is_followup = False

    def play_effect(self, game_state):
        player = game_state.current_player
        # Return this card to its supply pile rather than discarding it.
        # Only return if this physical copy is still in play; if a multiplier
        # (e.g., Throne Room) replays Experiment, the second resolution should
        # not add another phantom copy to the pile.
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.supply["Experiment"] = game_state.supply.get("Experiment", 0) + 1

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if self._is_followup:
            return
        if game_state.supply.get("Experiment", 0) <= 0:
            return
        from ..registry import get_card

        game_state.supply["Experiment"] -= 1
        bonus = get_card("Experiment")
        bonus._is_followup = True
        game_state.gain_card(player, bonus)

    def starting_supply(self, game_state) -> int:
        # Experiment uses a 10-card pile in the official rules.
        return 10
