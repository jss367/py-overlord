"""Conclave — $4 Action.

+$2. You may play an Action from hand you don't have a copy of in play.
If you do, +1 Action.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Conclave(Card):
    def __init__(self):
        super().__init__(
            name="Conclave",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        in_play_names = {c.name for c in player.in_play}
        choices = [
            c for c in player.hand
            if c.is_action and c.name not in in_play_names
        ]
        if not choices:
            return
        choice = player.ai.choose_action_to_play_with_conclave(
            game_state, player, choices
        )
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        game_state.log_callback(
            ("action", player.ai.name, f"Conclave plays {choice}", {})
        )
        choice.on_play(game_state)
        if not player.ignore_action_bonuses:
            player.actions += 1
