from .base_ally import Ally


class FellowshipOfScribes(Ally):
    """When you play a card, if you have 4 or fewer cards in hand, spend
    1 Favor for +1 Card.
    """

    def __init__(self):
        super().__init__("Fellowship of Scribes")

    def on_play_card(self, game_state, player, card) -> None:
        if player.favors <= 0:
            return
        if len(player.hand) > 4:
            return
        # Avoid recursion: only fire once per card play.
        player.favors -= 1
        game_state.draw_cards(player, 1)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "spends a Favor on Fellowship of Scribes (+1 Card)",
                {"favors_remaining": player.favors},
            )
        )
