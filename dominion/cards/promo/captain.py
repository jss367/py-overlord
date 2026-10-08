from ..base_card import Card, CardCost, CardStats, CardType
from ..supply_play import select_supply_action, supply_action_choices

class Captain(Card):
    """Command card that plays Actions from the Supply now and next turn."""

    def __init__(self):
        super().__init__(
            name="Captain",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.COMMAND],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        self._play_from_supply(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._play_from_supply(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def _play_from_supply(self, game_state, player):
        from ..registry import get_card

        candidates = supply_action_choices(game_state, player, 4, allow_duration=False)
        choice = select_supply_action(game_state, player, candidates, "choose_captain_target")
        if choice is None:
            return
        # "play a non-Duration Action card from the Supply costing up to $4,
        # leaving it there": a virtual play like Riverboat's. The proxy never
        # enters in_play, so Ways that move the played card (Turtle,
        # Butterfly, Horse, Worm) see it is not in play and leave the Supply
        # alone instead of stashing or returning a card the player never had.
        temp = get_card(choice.name)
        game_state.play_action_indirectly(player, temp)
