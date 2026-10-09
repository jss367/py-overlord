"""Context for free gains, independent of the purchase selector."""

from collections import Counter
from dataclasses import dataclass

from dominion.cards.base_card import Card


@dataclass(frozen=True)
class FreeGainContext:
    source: str
    destination: str
    hand: tuple[Card, ...]
    owned_counts: dict[str, int]
    endgame: bool
    sacrificed: Card | None = None
    mandatory: bool = True
    source_card: Card | None = None
    gain_number: int = 1
    previous_gain: Card | None = None
    can_trash_source: bool = False

    @classmethod
    def build(cls, state, player, source, destination="discard", sacrificed=None, mandatory=True,
              *, source_card=None, gain_number=1, previous_gain=None, can_trash_source=False):
        # Missing Province piles in small tactical fixtures do not signal an
        # endgame. Stored/exiled cards are included by all_cards().
        endgame = any(
            name in state.supply and state.supply[name] <= 2
            for name in ("Province", "Colony")
        ) or state.empty_piles >= 2
        return cls(source, destination, tuple(c for c in player.hand if c is not sacrificed),
                   dict(Counter(c.name for c in player.all_cards() if c is not sacrificed)),
                   endgame, sacrificed, mandatory, source_card, gain_number, previous_gain, can_trash_source)
