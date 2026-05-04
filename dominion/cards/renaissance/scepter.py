"""Scepter: Treasure ($5).

Choose one: $2; or replay an Action you have in play this turn.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Scepter(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Scepter",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Find Action cards in play that aren't durations remaining for
        # later turns (we treat any Action in play as eligible — Renaissance
        # rules require it was played this turn, which is true for anything
        # in player.in_play).
        replayable = [
            c
            for c in player.in_play
            if c.is_action and c is not self and c.name != "Scepter"
        ]
        if replayable:
            choice = max(
                replayable,
                key=lambda c: (c.cost.coins, c.stats.cards, c.name),
            )
            choice.on_play(game_state)
            game_state.fire_prophecy_action_hooks(player, choice)
        else:
            player.coins += 2
