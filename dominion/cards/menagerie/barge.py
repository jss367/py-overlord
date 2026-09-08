"""Barge - Action-Duration from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Barge(Card):
    """Either now or at the start of your next turn, +3 Cards and +1 Buy."""

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
        def resolve(choose_now):
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

        # Barge has an "either" timing choice, not a "choose" ability.
        resolve(choose_now)

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
