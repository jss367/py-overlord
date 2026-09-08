from .base_ally import Ally


class LeagueOfBankers(Ally):
    def __init__(self):
        super().__init__("League of Bankers")

    def on_buy_phase_start(self, game_state, player):
        player.coins += player.favors // 4
