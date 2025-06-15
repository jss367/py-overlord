from ..base_card import Card, CardCost, CardStats, CardType


class Taskmaster(Card):
    def __init__(self):
        super().__init__(
            name="Taskmaster",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if getattr(player, "gained_five_last_turn", False):
            if not player.ignore_action_bonuses:
                player.actions += 1
            player.coins += 1
            player.duration.append(self)
