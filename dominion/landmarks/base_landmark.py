"""Base class for Dominion landmarks.

Landmarks are static effects shared by all players that sit on the table
during the game. They are not in the supply and cannot be bought; most
modify scoring, while some adjust other game rules. Landmarks come from
Empires and are an alternative way to add interaction to a Kingdom.
"""

from dataclasses import dataclass


@dataclass
class Landmark:
    name: str

    def score(self, game_state, player) -> int:
        """Return the VP this landmark contributes to ``player`` at scoring."""
        return 0

    @property
    def is_landmark(self) -> bool:
        return True
