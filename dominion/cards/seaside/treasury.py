from ..base_card import Card, CardCost, CardStats, CardType


class Treasury(Card):
    """Action ($5): +1 Card, +1 Action, +$1.

    When you discard this from play, if you didn't gain a Victory card this
    turn, you may put this onto your deck.

    The engine fires :meth:`on_buy_phase_end` for every card in play just
    before cleanup begins (see ``GameState._handle_buy_phase_end``). This is
    the moment we'd otherwise discard Treasury, so it is the right place to
    intercept and topdeck it. Removing it from ``in_play`` here means the
    cleanup loop in ``GameState`` will skip it (it only iterates over what's
    still in ``in_play``).
    """

    def __init__(self):
        super().__init__(
            name="Treasury",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def on_buy_phase_end(self, game_state):
        player = game_state.current_player

        # "If you didn't gain a Victory card this turn" — checks every gain
        # this turn, not just gains during the Buy phase, so Workshop /
        # Charm / Ironworks etc. still block topdecking.
        if getattr(player, "gained_victory_this_turn", False):
            return

        # "you may put this onto your deck" — optional, defer to the AI.
        if not player.ai.should_topdeck_treasury(game_state, player):
            return

        if self in player.in_play:
            player.in_play.remove(self)
            # ``deck[-1]`` is the top of the deck (drawn next via deck.pop).
            player.deck.append(self)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    "topdecks Treasury",
                    {},
                )
            )
