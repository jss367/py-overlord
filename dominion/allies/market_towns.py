from .base_ally import Ally


class MarketTowns(Ally):
    """At start of Buy phase, spend 1+ Favors: play an Action from hand
    once per Favor.
    """

    def __init__(self):
        super().__init__("Market Towns")

    def on_buy_phase_start(self, game_state, player) -> None:
        while player.favors > 0:
            actions = [c for c in player.hand if c.is_action]
            if not actions:
                return
            choice = player.ai.choose_action(game_state, actions + [None])
            if choice is None or choice not in player.hand:
                return
            player.favors -= 1
            player.hand.remove(choice)
            player.in_play.append(choice)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"spends a Favor on Market Towns to play {choice}",
                    {"favors_remaining": player.favors},
                )
            )
            choice.on_play(game_state)
