"""Wall landmark from Empires: ``-1 VP per card you have over 15.``"""

from .base_landmark import Landmark


class Wall(Landmark):
    def __init__(self):
        super().__init__(name="Wall")

    def score(self, game_state, player) -> int:
        excess = max(0, len(player.all_cards()) - 15)
        return -excess
