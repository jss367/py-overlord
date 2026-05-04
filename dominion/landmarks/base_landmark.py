"""Base class for Empires Landmarks.

A Landmark is a persistent rules modifier added to the game alongside the
Kingdom. Landmarks contribute to scoring (``vp_for``) and may track per-pile
or per-Landmark VP via ``self.vp_pool`` (e.g. Aqueduct, Defiled Shrine,
Arena, Battlefield, Colonnade).
"""

from dataclasses import dataclass, field


@dataclass
class Landmark:
    name: str = ""
    description: str = ""

    # Per-Landmark VP pool (used by Aqueduct, Defiled Shrine, Arena, etc.)
    vp_pool: int = 0
    # Per-pile VP pool (Aqueduct moves VP from a Treasure pile to itself; etc).
    pile_vp: dict = field(default_factory=dict)
    # Setup-time chosen pile (Obelisk).
    chosen_pile: str = ""

    def setup(self, game_state) -> None:
        """Called once at game start to seed VP pools or choose piles."""
        pass

    def vp_for(self, game_state, player) -> int:
        """End-of-game VP contribution for a player.

        Most Landmarks add 0 here and instead grant VP tokens during play.
        """
        return 0

    # Hooks fired throughout the game.
    def on_buy(self, game_state, player, card) -> None:
        pass

    def on_gain(self, game_state, player, card) -> None:
        pass

    def on_trash(self, game_state, player, card) -> None:
        pass

    def on_buy_phase_start(self, game_state, player) -> None:
        pass
