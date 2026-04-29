"""Regression test: Cartographer must not crash when two top-4 cards tie on score.

The original `kept.sort()` on a list of `(int, Card)` tuples fell back to comparing
Card instances when scores tied, raising TypeError because Card has no __lt__.
"""

from dominion.cards.registry import get_card
from dominion.cards.hinterlands.cartographer import Cartographer


def test_cartographer_does_not_crash_when_scores_tie():
    """Two Coppers in the revealed pile both score 2 — sorting must not compare cards."""
    import types

    cartographer = Cartographer()

    copper_a = get_card("Copper")
    copper_b = get_card("Copper")
    silver = get_card("Silver")
    estate = get_card("Estate")

    discarded: list = []
    player = types.SimpleNamespace(
        deck=[estate, copper_a, copper_b, silver],  # popped in reverse: silver, copper_b, copper_a, estate
        discard=[],
        shuffle_discard_into_deck=lambda: None,
    )

    game_state = types.SimpleNamespace(
        current_player=player,
        discard_card=lambda p, c: discarded.append(c),
    )

    # Should not raise.
    cartographer.play_effect(game_state)

    # Estate (score -2) was discarded; the rest are kept on top of the deck.
    assert estate in discarded
    assert all(c.name in {"Silver", "Copper"} for c in player.deck)
