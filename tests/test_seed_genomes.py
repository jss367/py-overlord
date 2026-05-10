"""Tests for ``dominion.analysis.seed_genomes``.

Each Interaction kind has a unit test using a synthetic ``BoardConfig``.
The acceptance test from issue #232 — running the seed builder on
``boards/victoria_kingdom.txt`` produces a strategy that uses Way of the
Butterfly on Flag Bearer — is covered explicitly.
"""

from __future__ import annotations

from pathlib import Path

from dominion.analysis.seed_genomes import (
    build_seed_genomes,
    trick_signature,
)
from dominion.analysis.trick_scanner import Interaction, scan
from dominion.boards.loader import BoardConfig, load_board
from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
VICTORIA_BOARD = REPO_ROOT / "boards" / "victoria_kingdom.txt"


def _board(**kwargs) -> BoardConfig:
    kingdom = kwargs.pop("kingdom_cards")
    return BoardConfig(kingdom_cards=list(kingdom), **kwargs)


# --- Acceptance: issue #232 -------------------------------------------------


def test_acceptance_victoria_seeds_include_butterfly_flag_bearer():
    """Issue #232 acceptance: running the seed builder on victoria_kingdom
    produces at least one seed that uses Way of the Butterfly on Flag
    Bearer (i.e. has a ``WayRule(card_name='Flag Bearer',
    way_name='Way of the Butterfly')``)."""

    board = load_board(VICTORIA_BOARD)

    seeds = build_seed_genomes(board)

    matching: list[tuple[str, EnhancedStrategy]] = []
    for name, strategy in seeds:
        for rule in strategy.way_policy:
            if (
                rule.card_name == "Flag Bearer"
                and rule.way_name == "Way of the Butterfly"
            ):
                matching.append((name, strategy))
                break
    assert matching, (
        "Expected build_seed_genomes(victoria_kingdom) to include a seed with "
        "WayRule('Flag Bearer', 'Way of the Butterfly'). Got seeds: "
        f"{[name for name, _ in seeds]}"
    )


# --- Per-kind unit tests ----------------------------------------------------


def test_trash_hook_seed_emits_butterfly_way_policy():
    board = _board(
        kingdom_cards=["Flag Bearer", "Village", "Smithy"],
        ways=["Way of the Butterfly"],
    )

    seeds = build_seed_genomes(board)

    butterfly_seeds = [
        (name, s)
        for name, s in seeds
        if any(
            r.card_name == "Flag Bearer" and r.way_name == "Way of the Butterfly"
            for r in s.way_policy
        )
    ]
    assert butterfly_seeds, [name for name, _ in seeds]

    name, strategy = butterfly_seeds[0]
    # Sanity: the seed must also gain Flag Bearer (otherwise the way policy
    # never fires) and have a treasure priority list (so it can pay).
    gain_cards = [r.card for r in strategy.gain_priority]
    assert "Flag Bearer" in gain_cards
    assert any(r.card == "Gold" for r in strategy.treasure_priority)
    assert any(r.card == "Province" for r in strategy.gain_priority)


def test_gain_hook_seed_prioritises_hook_card():
    """Flag Bearer + Duplicate triggers the gain-hook predicate; the seed
    should put Flag Bearer high in the gain priority so each gainer
    re-fires its on_gain hook."""

    board = _board(kingdom_cards=["Flag Bearer", "Duplicate"])

    seeds = build_seed_genomes(board)

    re_gain_seeds = [s for name, s in seeds if name.startswith("Trick Re-gain")]
    assert re_gain_seeds, [name for name, _ in seeds]

    flag_bearer_seed = next(
        s for s in re_gain_seeds if "Flag Bearer" in (s.name or "")
    )
    gain_cards = [r.card for r in flag_bearer_seed.gain_priority]
    assert "Flag Bearer" in gain_cards
    # The hook card should rank ahead of the generic Silver fallback.
    assert gain_cards.index("Flag Bearer") < gain_cards.index("Silver")


def test_empty_deck_event_seed_buys_event_and_self_exile_card():
    board = _board(
        kingdom_cards=["Stockpile", "Village"],
        events=["Windfall"],
    )

    seeds = build_seed_genomes(board)

    empty_seeds = [s for _, s in seeds if any(r.card == "Windfall" for r in s.gain_priority)]
    assert empty_seeds, [name for name, _ in seeds]

    seed = empty_seeds[0]
    gain_cards = [r.card for r in seed.gain_priority]
    assert "Windfall" in gain_cards
    assert "Stockpile" in gain_cards
    # Windfall (the payoff event) should come before the generic Silver.
    assert gain_cards.index("Windfall") < gain_cards.index("Silver")


def test_command_seed_pairs_command_with_top_payload_target():
    board = _board(
        kingdom_cards=["Band of Misfits", "Witch", "Village", "Smithy"],
    )

    seeds = build_seed_genomes(board)

    command_seeds = [s for name, s in seeds if name.startswith("Trick Band of Misfits")]
    assert command_seeds, [name for name, _ in seeds]

    seed = command_seeds[0]
    gain_cards = [r.card for r in seed.gain_priority]
    assert "Band of Misfits" in gain_cards

    # Action priority must play the Command FIRST so its pending-replay
    # slot is registered, then the payload that consumes the slot. The
    # reverse order silently breaks every "next non-Command Action"
    # Command (Daimyo, Flagship): the payload would be played first and
    # the Command's pending counter would have nothing to fire on for the
    # rest of the turn.
    action_cards = [r.card for r in seed.action_priority]
    assert action_cards[0] == "Band of Misfits", action_cards
    assert action_cards[1] in {"Witch", "Smithy", "Village"}, action_cards


def test_cost_mod_seed_stacks_reducer():
    board = _board(kingdom_cards=["Bridge", "Village", "Smithy"])

    seeds = build_seed_genomes(board)

    cost_mod_seeds = [s for name, s in seeds if name.startswith("Trick Cost-mod")]
    assert cost_mod_seeds, [name for name, _ in seeds]

    seed = cost_mod_seeds[0]
    gain_cards = [r.card for r in seed.gain_priority]
    assert "Bridge" in gain_cards


# --- Misc -------------------------------------------------------------------


def test_build_seed_genomes_drops_unknown_kinds_silently():
    """Interactions with kinds the seed builder doesn't know about must be
    skipped without raising — keeps adding new trick scanner predicates
    backwards-compatible with this module."""

    board = _board(kingdom_cards=["Village"])
    fake = Interaction(kind="brand_new_kind_no_builder", headline="x")

    seeds = build_seed_genomes(board, interactions=[fake])

    assert seeds == []


def test_build_seed_genomes_dedupes_by_name():
    """Two Interactions producing the same seed name (e.g. duplicated
    re-trigger sources for the same hook card) must collapse to one seed."""

    board = _board(kingdom_cards=["Flag Bearer", "Duplicate", "Workshop"])

    interactions = scan(board)
    seeds = build_seed_genomes(board, interactions=interactions)
    names = [name for name, _ in seeds]

    assert len(names) == len(set(names))


def test_trick_signature_captures_way_policy_and_gain_cards():
    s = EnhancedStrategy()
    s.gain_priority = [PriorityRule("Province"), PriorityRule("Flag Bearer")]
    s.action_priority = [PriorityRule("Flag Bearer")]
    s.way_policy = [WayRule(card_name="Flag Bearer", way_name="Way of the Butterfly")]

    sig = trick_signature(s)

    assert "Flag Bearer->Way of the Butterfly" in sig["way_policy"]
    assert "Flag Bearer" in sig["gain_cards"]
    assert "Flag Bearer" in sig["action_cards"]
