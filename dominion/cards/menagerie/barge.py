"""Barge - Action-Duration from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Barge(Card):
    """Choose one: +3 Cards +1 Buy now; or +3 Cards +1 Buy at start of your
    next turn.
    """

    def __init__(self):
        super().__init__(
            name="Barge",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self._fire_now = False

    def play_effect(self, game_state):
        player = game_state.current_player
        choose_now = player.ai.should_resolve_barge_now(game_state, player)
        if choose_now:
            game_state.draw_cards(player, 3)
            player.buys += 1
            # Not a duration this turn; remove from in_play normally during
            # cleanup. Default behaviour does this.
        else:
            self._fire_now = True
            player.duration.append(self)
            self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self._fire_now:
            game_state.draw_cards(player, 3)
            player.buys += 1
            self._fire_now = False
        self.duration_persistent = False
