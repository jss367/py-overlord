from .base_ally import Ally


class CityState(Ally):
    """When you play a Treasure, you may spend 2 Favors to play an Action
    from hand.
    """

    def __init__(self):
        super().__init__("City-state")

    def on_play_card(self, game_state, player, card) -> None:
        if not card.is_treasure:
            return
        if player.favors < 2:
            return
        # Only fire during Treasure phase to avoid recursing on
        # in-Action-phase Treasure plays.
        if game_state.phase != "buy" and game_state.phase != "treasure":
            return
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            return
        player.favors -= 2
        player.hand.remove(choice)
        player.in_play.append(choice)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends 2 Favors on City-state to play {choice}",
                {"favors_remaining": player.favors},
            )
        )
        choice.on_play(game_state)
