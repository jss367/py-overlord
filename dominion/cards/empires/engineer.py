from ..base_card import Card, CardCost, CardStats, CardType


class Engineer(Card):
    def __init__(self):
        super().__init__(
            name="Engineer",
            cost=CardCost(debt=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        from dominion.ai.gain_context import FreeGainContext
        from ..gain_decisions import choose_free_gain, gain_menu, gain_selected

        def gain(number, previous=None):
            choices = gain_menu(game_state, player, CardCost(coins=4))
            choices.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            context = FreeGainContext.build(
                game_state, player, self.name, source_card=self, gain_number=number,
                previous_gain=previous, can_trash_source=self in player.in_play,
                sacrificed=self if number == 2 else None,
            )
            choice = choose_free_gain(game_state, player, choices, self.name, context=context)
            gained = []
            gain_selected(game_state, player, choice, choices=choices,
                          source=self.name, context=context, gain_observer=gained.append)
            return gained[0] if gained else None

        first = gain(1)
        if self not in player.in_play:
            return
        if not player.ai.should_trash_engineer_for_extra_gains(game_state, player, self):
            return
        # The hook can itself move the source; self-trash must still succeed.
        if self not in player.in_play:
            return
        player.in_play.remove(self)
        game_state.trash_card(player, self)
        gain(2, first)
