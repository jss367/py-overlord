from dataclasses import dataclass
from typing import ClassVar

@dataclass
class Way:
    name: str

    # True for Ways whose instructions are carried out by invoking a card's
    # on_play as a proxy: Chameleon (the played card), Mouse (the set-aside
    # card). Only these arm GameState's proxy flag
    # (``_way_proxy_play_active``), which makes that one on_play skip the
    # per-play bonuses and reactions the Way branch applies itself. Any
    # other Way runs with the flag clear, so a play its instructions
    # trigger some other way (Butterfly's or Rat's gain reaching Innovation,
    # which plays the gained card directly) is a real play with all of its
    # side effects. A ClassVar, not a dataclass field: subclasses override
    # it at class level and the generated __init__ must not shadow that.
    uses_on_play_proxy: ClassVar[bool] = False

    def apply(self, game_state, card) -> None:
        """Apply this Way's effect when the given card is played."""
        pass

    @property
    def is_way(self) -> bool:
        return True
