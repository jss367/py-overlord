"""Tests for ``dominion.analysis.trick_scanner``.

Each predicate is exercised in isolation against a synthetic ``BoardConfig`` so the
test stays focused on a single mechanic. Two end-to-end acceptance tests cover the
real ``boards/victoria_kingdom.txt`` and ``boards/iron_barbarian.txt`` files referenced
in issue #230.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dominion.analysis.trick_scanner import (
    Interaction,
    main,
    predicate_command_targets,
    predicate_cost_mod_gateways,
    predicate_empty_deck_discard_triggers,
    predicate_gain_hook_retriggerable,
    predicate_trash_hook_via_return_to_supply,
    render_markdown,
    scan,
)
from dominion.boards.loader import BoardConfig, load_board

REPO_ROOT = Path(__file__).resolve().parent.parent
VICTORIA_BOARD = REPO_ROOT / "boards" / "victoria_kingdom.txt"
IRON_BARBARIAN_BOARD = REPO_ROOT / "boards" / "iron_barbarian.txt"


def _board(**kwargs) -> BoardConfig:
    kingdom = kwargs.pop("kingdom_cards")
    return BoardConfig(kingdom_cards=list(kingdom), **kwargs)


# --- Predicate 1: trash hook unreachable via return-to-supply Way --------


def test_trash_hook_predicate_flags_flag_bearer_with_butterfly():
    board = _board(
        kingdom_cards=["Flag Bearer", "Village"],
        ways=["Way of the Butterfly"],
    )

    interactions = predicate_trash_hook_via_return_to_supply(board)

    assert len(interactions) == 1
    headline = interactions[0].headline
    assert "Flag Bearer" in headline
    assert "Way of the Butterfly" in headline
    assert "on_trash" in headline


def test_trash_hook_predicate_silent_without_butterfly():
    board = _board(kingdom_cards=["Flag Bearer", "Village"])

    assert predicate_trash_hook_via_return_to_supply(board) == []


def test_trash_hook_predicate_silent_when_no_card_has_on_trash_override():
    board = _board(
        kingdom_cards=["Village", "Smithy"],
        ways=["Way of the Butterfly"],
    )

    assert predicate_trash_hook_via_return_to_supply(board) == []


# --- Predicate 2: gain hook re-triggerable -------------------------------


def test_gain_hook_predicate_flag_bearer_with_duplicate():
    board = _board(kingdom_cards=["Flag Bearer", "Duplicate"])

    interactions = predicate_gain_hook_retriggerable(board)

    assert len(interactions) == 1
    interaction = interactions[0]
    assert "Flag Bearer" in interaction.headline
    assert "Duplicate" in interaction.headline


def test_gain_hook_predicate_butterfly_counts_as_a_gainer():
    board = _board(
        kingdom_cards=["Flag Bearer", "Village"],
        ways=["Way of the Butterfly"],
    )

    interactions = predicate_gain_hook_retriggerable(board)

    assert len(interactions) == 1
    assert "Way of the Butterfly" in interactions[0].headline


def test_gain_hook_predicate_silent_without_gainers():
    board = _board(kingdom_cards=["Flag Bearer", "Village", "Smithy"])

    assert predicate_gain_hook_retriggerable(board) == []


# --- Predicate 3: empty-deck/discard triggers ---------------------------


def test_empty_deck_discard_stockpile_plus_windfall():
    board = _board(kingdom_cards=["Stockpile", "Village"], events=["Windfall"])

    interactions = predicate_empty_deck_discard_triggers(board)

    assert len(interactions) == 1
    assert "Stockpile" in interactions[0].headline
    assert "Windfall" in interactions[0].headline


def test_empty_deck_discard_silent_without_event():
    board = _board(kingdom_cards=["Stockpile"])

    assert predicate_empty_deck_discard_triggers(board) == []


def test_empty_deck_discard_silent_without_self_exile_card():
    board = _board(kingdom_cards=["Village"], events=["Windfall"])

    assert predicate_empty_deck_discard_triggers(board) == []


def test_empty_deck_discard_does_not_flag_native_village():
    # Native Village sets aside the top of the deck onto its mat — Native
    # Village itself stays in play and discards normally, so it must not be
    # treated as a self-exile/set-aside card.
    board = _board(kingdom_cards=["Native Village"], events=["Windfall"])

    assert predicate_empty_deck_discard_triggers(board) == []


# --- Predicate 4: command targets ---------------------------------------


def test_command_targets_lists_actions_for_daimyo():
    board = _board(kingdom_cards=["Daimyo", "Smithy", "Village"])

    interactions = predicate_command_targets(board)

    assert len(interactions) == 1
    interaction = interactions[0]
    assert "Daimyo" in interaction.headline
    assert "Smithy" in interaction.detail


def test_command_targets_silent_without_command_card():
    board = _board(kingdom_cards=["Smithy", "Village"])

    assert predicate_command_targets(board) == []


def test_command_targets_silent_without_non_command_action_targets():
    board = _board(kingdom_cards=["Daimyo"])

    assert predicate_command_targets(board) == []


# --- Predicate 5: cost-mod gateways -------------------------------------


def test_cost_mod_gateways_bridge():
    board = _board(kingdom_cards=["Bridge", "Smithy", "Nobles"])

    interactions = predicate_cost_mod_gateways(board)

    assert len(interactions) == 1
    interaction = interactions[0]
    assert "Bridge" in interaction.headline
    assert "Province" in interaction.detail
    # Threshold summary should mention both kingdom-card cost lines.
    assert "$4" in interaction.detail
    assert "$6" in interaction.detail


def test_cost_mod_gateways_highway():
    board = _board(kingdom_cards=["Highway", "Smithy"])

    interactions = predicate_cost_mod_gateways(board)

    assert len(interactions) == 1
    assert "Highway" in interactions[0].headline


def test_cost_mod_gateways_silent_without_cost_modifier():
    board = _board(kingdom_cards=["Smithy", "Village"])

    assert predicate_cost_mod_gateways(board) == []


# --- Acceptance: full scans on real boards from issue #230 --------------


def test_acceptance_victoria_board_surfaces_flag_bearer_butterfly():
    board = load_board(VICTORIA_BOARD)

    interactions = scan(board)

    matching = [
        i
        for i in interactions
        if i.kind == "trash_hook_unreachable"
        and "Flag Bearer" in i.headline
        and "Way of the Butterfly" in i.headline
    ]
    assert matching, (
        "Expected scan(victoria_kingdom) to surface Flag Bearer + Way of the Butterfly "
        "trash-hook interaction; got: "
        f"{[i.headline for i in interactions]}"
    )


def test_acceptance_iron_barbarian_board_surfaces_at_least_one_interaction():
    board = load_board(IRON_BARBARIAN_BOARD)

    interactions = scan(board)

    assert interactions, (
        "Expected scan(iron_barbarian) to surface at least one interaction "
        "(Bridge cost-mod gateway, at minimum)."
    )


# --- Output rendering ----------------------------------------------------


def test_render_markdown_includes_kingdom_landscapes_and_interactions():
    board = load_board(VICTORIA_BOARD)
    interactions = scan(board)

    md = render_markdown(VICTORIA_BOARD, board, interactions)

    assert "Trick scan" in md
    assert "Flag Bearer" in md
    assert "Windfall" in md
    assert "Way of the Butterfly" in md


def test_render_markdown_handles_empty_interactions():
    board = _board(kingdom_cards=["Village"])

    md = render_markdown("synthetic.txt", board, [])

    assert "_No interactions surfaced._" in md


def test_interaction_to_markdown_skips_empty_refs():
    interaction = Interaction(
        kind="x",
        headline="Headline",
        detail="Detail",
        refs=["", "/path:42"],
    )

    text = interaction.to_markdown()

    assert "**Headline**" in text
    assert "/path:42" in text
    # An empty ref must not produce a bare backtick line.
    assert "`\n" not in text
    assert "``" not in text


# --- CLI -----------------------------------------------------------------


def test_main_runs_against_victoria_board(capsys):
    exit_code = main(["--board", str(VICTORIA_BOARD)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Flag Bearer" in captured.out
    assert "Way of the Butterfly" in captured.out


def test_main_errors_on_missing_board(tmp_path):
    with pytest.raises(FileNotFoundError):
        main(["--board", str(tmp_path / "does_not_exist.txt")])
