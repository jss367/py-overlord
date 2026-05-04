from .base_ally import Ally


class LeagueOfBankers(Ally):
    """At end of Buy phase, +$1 per 4 Favors you have.

    Hooked via ``on_buy_phase_end`` so the bonus contributes to a
    re-entered buy if the engine ever loops; in practice the buy phase
    has already ended and this records VP/Coin tokens. Treat this as +$
    that converts to a token gain for simplicity.
    """

    def __init__(self):
        super().__init__("League of Bankers")

    def on_buy_phase_end(self, game_state, player) -> None:
        bonus = player.favors // 4
        if bonus <= 0:
            return
        # Convert to coin tokens since the buy phase is already over.
        player.coin_tokens += bonus
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"League of Bankers grants +{bonus} coin tokens (Favors: {player.favors})",
                {"favors_remaining": player.favors},
            )
        )
