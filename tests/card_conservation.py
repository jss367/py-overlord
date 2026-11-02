"""Conservation checks for closed fixtures with normal Supply piles.

Use physical zones rather than all_cards(), whose deduplication can hide a card
in two places. Duration queues contain instruction references; older cards may
also use them as the sole location of their physical source. Setup-only cards
and other global decks are outside these fixtures' inventory contract.
"""

from collections import Counter
from contextlib import contextmanager


def inventory(state):
    """Count Supply, owned zones, and trash; reject invalid physical locations."""
    for name, count in state.supply.items():
        assert count >= 0, f"negative Supply count: {name}={count}"
    counts = Counter({name: n for name, n in state.supply.items() if name not in state.pile_order})
    for pile, names in state.pile_order.items():
        assert state.supply[pile] == len(names), (
            f"pile accounting mismatch: {pile} has {state.supply[pile]} in Supply but {len(names)} ordered cards"
        )
        counts.update(names)

    locations = {}

    def add(card, location):
        assert not getattr(card, "virtual_supply_play", False), f"virtual card {card.name} in {location}"
        assert not getattr(card, "returned_to_supply", False), f"returned card {card.name} still in {location}"
        previous = locations.get(id(card))
        assert previous is None, f"{card.name} occupies multiple physical zones: {previous} and {location}"
        locations[id(card)] = location
        counts[card.name] += 1

    for index, player in enumerate(state.players):
        for zone_index, zone in enumerate(player._physical_card_zones()):
            for offset, card in enumerate(zone):
                add(card, f"player[{index}].physical_zone[{zone_index}][{offset}]")
    for index, card in enumerate(state.trash):
        add(card, f"trash[{index}]")

    # A transferred or trashed source can remain in its old owner's queue.
    # Its real location takes precedence over every pending reference.
    physical = set(locations)
    pending_owners = {}
    for index, player in enumerate(state.players):
        for card in player.duration + player.multiplied_durations + player._resolving_duration_sources:
            if id(card) in physical or getattr(card, "virtual_supply_play", False) or getattr(card, "returned_to_supply", False):
                continue
            previous = pending_owners.setdefault(id(card), index)
            assert previous == index, f"{card.name} has only pending references from multiple owners"
            if id(card) not in locations:
                add(card, f"player[{index}].duration_only")
    return +counts


class CardConservation:
    """Keep a baseline and annotate every failing transition with its seed."""

    def __init__(self, state, *, seed):
        self.seed = seed
        try:
            self.expected = inventory(state)
        except Exception as error:
            self._annotate(error, state, "initial inventory")
            raise

    def _annotate(self, error, state, step):
        context = (f"seed={self.seed}; step={step}; phase={state.phase}; "
                   f"turn={state.turn_number}; player={state.current_player_index}")
        if context not in getattr(error, "__notes__", []):
            error.add_note(context)

    def check(self, state, step):
        """Assert card totals and locations without using the ownership deduper."""
        try:
            actual = inventory(state)
            assert actual == self.expected, (
                f"card inventory changed: missing={dict(self.expected - actual)}, "
                f"extra={dict(actual - self.expected)}"
            )
        except Exception as error:
            self._annotate(error, state, step)
            raise

    @contextmanager
    def step(self, state, label):
        """Check conservation after an operation and annotate its own assertions."""
        try:
            yield
            self.check(state, label)
        except Exception as error:
            self._annotate(error, state, label)
            raise
