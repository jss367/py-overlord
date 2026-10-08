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

    @classmethod
    def build(cls, state, player, source, destination="discard", sacrificed=None, mandatory=True):
        # Missing Province piles in small tactical fixtures do not signal an
        # endgame. Stored/exiled cards are included by all_cards().
        endgame = any(
            name in state.supply and state.supply[name] <= 2
            for name in ("Province", "Colony")
        ) or sum(count == 0 for count in state.supply.values()) >= 2
        return cls(source, destination, tuple(c for c in player.hand if c is not sacrificed),
                   dict(Counter(c.name for c in player.all_cards() if c is not sacrificed)),
                   endgame, sacrificed, mandatory)
