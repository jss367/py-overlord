from .base_ally import Ally


class DesertGuides(Ally):
    """At start of turn, spend 1 Favor: discard hand and draw 5. May
    repeat.
    """

    def __init__(self):
        super().__init__("Desert Guides")

    def on_turn_start(self, game_state, player) -> None:
        # Repeat while hand looks bad and Favors are available.
        while player.favors > 0 and player.hand:
            junk = sum(
                1 for c in player.hand
                if c.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}
                or (c.is_victory and not c.is_action and c.cost.coins <= 2)
            )
            if junk < 3 and len(player.hand) >= 4:
                return
            old_hand = list(player.hand)
            player.hand = []
            for card in old_hand:
                game_state.discard_card(player, card)
            game_state.draw_cards(player, 5)
            player.favors -= 1
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    "spends a Favor on Desert Guides (discard hand, draw 5)",
                    {"favors_remaining": player.favors},
                )
            )
