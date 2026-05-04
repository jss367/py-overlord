"""Piazza: at the start of your turn, reveal the top card. If it's an Action,
play it."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Piazza(Project):
    def __init__(self) -> None:
        super().__init__("Piazza", CardCost(coins=5))

    def on_turn_start(self, game_state, player) -> None:
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        top = player.deck.pop()

        if top.is_action:
            player.in_play.append(top)
            top.on_play(game_state)
            game_state.fire_prophecy_action_hooks(player, top)
            game_state.fire_ally_play_hooks(player, top)
            game_state.log_callback(
                ("action", player.ai.name, f"plays {top.name} via Piazza", {}),
            )
        else:
            # Not an Action: put it back on top.
            player.deck.append(top)
