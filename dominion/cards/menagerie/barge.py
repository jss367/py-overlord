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
        # Lazy import to avoid circular import (ways package imports
        # cards registry at top level).
        from dominion.ways.chameleon import chameleon_plus_cards

        player = game_state.current_player
        choose_now = player.ai.should_resolve_barge_now(game_state, player)
        if choose_now:
            # "+3 Cards" instruction — Way of the Chameleon swaps to +$3.
            chameleon_plus_cards(game_state, player, 3)
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
            # Duration "+3 Cards" — fires next turn, when the chosen-card
            # Chameleon resolution has long ended, so it never swaps. Use
            # the regular draw path.
            game_state.draw_cards(player, 3)
            player.buys += 1
            self._fire_now = False
        self.duration_persistent = False
