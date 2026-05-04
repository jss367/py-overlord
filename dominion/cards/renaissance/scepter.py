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

        # Renaissance rules: Scepter replays an Action played THIS turn.
        # Duration cards from prior turns linger in ``player.in_play`` but
        # are no longer tracked in ``player.duration`` /
        # ``player.multiplied_durations`` (they were resolved and removed
        # at the start of this turn). Exclude them so we don't illegally
        # replay them this turn.
        active_durations = set(map(id, player.duration)) | set(
            map(id, player.multiplied_durations)
        )
        replayable = [
            c
            for c in player.in_play
            if c.is_action
            and c is not self
            and c.name != "Scepter"
            and (not c.is_duration or id(c) in active_durations)
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
