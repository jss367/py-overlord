from .base_ally import Ally


class FellowshipOfScribes(Ally):
    """After playing an Action with 4 or fewer cards in hand, you may spend
    1 Favor for +1 Card.
    """

    def __init__(self):
        super().__init__("Fellowship of Scribes")

    def on_play_card(self, game_state, player, card) -> None:
        if not card.is_action or player.favors <= 0:
            return
        if len(player.hand) > 4:
            return
        from ..cards.allies._rules import decide

        if not decide(
            game_state, player, "fellowship_of_scribes", [False, True], True
        ):
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
