from ..base_card import Card, CardCost, CardStats, CardType


class Riverboat(Card):
    """Action-Duration ($3):
    At the start of your next turn, play the Riverboat card (a non-Duration
    Action card costing exactly $5, chosen at game setup and set aside).
    """

    def __init__(self):
        super().__init__(
            name="Riverboat",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Stay in play until the set-aside card is played next turn.
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        target = game_state.riverboat_set_aside
        if target is None:
            self.duration_persistent = False
            return
        # Play the set-aside card without moving it from its set-aside
        # location. It doesn't count as in-play but its effects still resolve
        # (per rulebook: "This doesn't move the set aside card; it stays set
        # aside, even if it has instructions on it that would move it.").
        target.on_play(game_state)
        # Active prophecies (Great Leader, Approaching Army, etc.) react to
        # this play just like an Action-phase play would.
        game_state.fire_prophecy_action_hooks(player, target)
        self.duration_persistent = False
