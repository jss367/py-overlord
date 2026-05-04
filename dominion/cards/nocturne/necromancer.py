"""Necromancer — $4 Action.

Play a non-Command Action card from the trash, leaving it there.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Necromancer(Card):
    nocturne_piles = {
        "Zombie Apprentice": 1,
        "Zombie Mason": 1,
        "Zombie Spy": 1,
    }

    def __init__(self):
        super().__init__(
            name="Necromancer",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Identify non-Command Action cards in the trash
        choices = [
            c for c in game_state.trash
            if c.is_action and not c.is_command
        ]
        if not choices:
            return
        choice = player.ai.choose_action_to_play_from_trash(
            game_state, player, choices
        )
        if choice is None or choice not in game_state.trash:
            return
        # Play but leave in trash
        game_state.log_callback(
            ("action", player.ai.name, f"Necromancer plays {choice} from trash", {})
        )
        choice.on_play(game_state)
        game_state.fire_ally_play_hooks(player, choice)
