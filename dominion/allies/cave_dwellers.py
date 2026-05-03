from .base_ally import Ally


class CaveDwellers(Ally):
    """Cave Dwellers (Allies).

    Simplified rules used here: at the start of your turn, while you have
    Favors, you may spend them one at a time to discard a card from your
    hand and then draw a card. Repeat as the AI desires.
    """

    def __init__(self):
        super().__init__("Cave Dwellers")

    def on_turn_start(self, game_state, player) -> None:
        ai = player.ai
        while player.favors > 0 and player.hand:
            if not ai.should_spend_favor_on_cave_dwellers(game_state, player):
                return

            choice = ai.choose_card_to_discard_for_cave_dwellers(
                game_state, player, list(player.hand)
            )
            if choice is None or choice not in player.hand:
                return

            player.favors -= 1
            player.hand.remove(choice)
            game_state.discard_card(player, choice)
            game_state.draw_cards(player, 1)
            game_state.log_callback(
                (
                    "action",
                    ai.name,
                    f"spends a Favor on Cave Dwellers, discards {choice} and draws a card",
                    {"favors_remaining": player.favors},
                )
            )
