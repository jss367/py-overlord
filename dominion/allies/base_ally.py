from dataclasses import dataclass


@dataclass
class Ally:
    """Base class for Allies (from the Allies expansion).

    Allies are revealed once per game when at least one Liaison is in the
    kingdom. Liaison cards grant the controlling player Favor tokens, which
    can be spent to activate the Ally's effect.
    """

    name: str

    def on_turn_start(self, game_state, player) -> None:
        """Hook fired at the start of every player's turn."""

    @property
    def is_ally(self) -> bool:
        return True
