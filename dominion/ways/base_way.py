from dataclasses import dataclass

@dataclass
class Way:
    name: str

    def apply(self, game_state, card) -> None:
        """Apply this Way's effect when the given card is played."""
        pass

    @property
    def is_way(self) -> bool:
        return True
