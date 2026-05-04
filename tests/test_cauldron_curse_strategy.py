"""Smoke and behavioural tests for the CauldronCurse seed strategy.

These tests verify three things:

1. The strategy and the matching ``boards/cauldron_curse.txt`` board can
   both be loaded and used by the existing simulation harness.
2. A single end-to-end game on the seed board completes without crashing
   and the strategy populates a deck of the expected shape (Cauldron and
   Workshop both present, no Curses self-junked).
3. Across a small batch of games against ``BigMoney`` the strategy wins
   a respectable share of games and at least one Curse is delivered to
   the opponent (i.e. the Cauldron-trigger plan is firing at least
   sometimes - it is otherwise extremely rare for Big Money to ever
   gain a Curse, since this board has no other curse-giving card).
"""

from __future__ import annotations

import contextlib
import io
import random
from pathlib import Path

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.strategy_loader import StrategyLoader

BOARD_PATH = Path("boards/cauldron_curse.txt")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def loader() -> StrategyLoader:
    return StrategyLoader()


@pytest.fixture(scope="module")
def board():
    return load_board(BOARD_PATH)


def _silent_play(gs: GameState) -> None:
    """Play a single game while suppressing the engine's chatty stdout
    logging - the engine's default ``log_callback`` prints every event."""
    with contextlib.redirect_stdout(io.StringIO()):
        while not gs.is_game_over():
            gs.play_turn()


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


def test_strategy_is_registered(loader):
    """The strategy loader picks up the new file via its ``create_*``
    factory and exposes both the display name and the slug alias."""
    strategy = loader.get_strategy("CauldronCurse")
    assert strategy is not None
    assert strategy.name == "CauldronCurse"
    # The slug alias should also resolve.
    assert loader.get_strategy("cauldron_curse").name == "CauldronCurse"


def test_board_file_lists_required_pieces(board):
    """The seed board must include the curse keystone (Cauldron) plus a
    handful of cheap actions and a +Buy source - exactly the set the
    strategy is hand-tuned for."""
    kingdom = board.kingdom_cards
    assert "Cauldron" in kingdom
    # At least three actions costing <= $4.
    cheap_actions = {
        name
        for name in kingdom
        if get_card(name).is_action and get_card(name).cost.coins <= 4
    }
    assert len(cheap_actions) >= 3, cheap_actions
    # +Buy comes from Cauldron itself (+1 Buy on every play); Hamlet
    # and Pawn also offer optional +Buy on this board.
    assert "Hamlet" in kingdom or "Pawn" in kingdom


def test_single_game_runs_without_error(loader, board):
    """A single end-to-end game on the seed board completes and the
    CauldronCurse player ends up with the keystone cards in their deck."""
    strat1 = loader.get_strategy("CauldronCurse")
    strat2 = loader.get_strategy("BigMoney")
    ai1 = GeneticAI(strat1)
    ai2 = GeneticAI(strat2)
    kingdom_cards = [get_card(name) for name in board.kingdom_cards]
    gs = GameState(players=[], supply={})
    gs.initialize_game([ai1, ai2], kingdom_cards, use_shelters=False)

    _silent_play(gs)

    cc_player = next(p for p in gs.players if p.ai is ai1)
    deck_names = {c.name for c in cc_player.all_cards()}
    assert "Cauldron" in deck_names, "Strategy never bought the keystone"
    # The strategy should never voluntarily buy a Curse.
    assert sum(1 for c in cc_player.all_cards() if c.name == "Curse") == 0


# ---------------------------------------------------------------------------
# Behavioural test - vs Big Money on the seed board
# ---------------------------------------------------------------------------


def test_strategy_competitive_vs_big_money(loader, board):
    """Across a moderate batch of seeded games CauldronCurse should win
    a competitive share of games against vanilla Big Money on the
    cauldron_curse board.

    We deliberately seed Python's RNG to make this test deterministic
    so flakiness in the strategy frame doesn't break CI. With Cauldron
    at its printed cost of $5, the strategy's empirical winrate is
    around 30%; the ``>= 10`` threshold (25%) is set well below that
    but still high enough that a regression which broke the Cauldron
    curse-out attack or the strategy frame would surface."""

    random.seed(20240429)
    cc_wins = 0
    bm_wins = 0
    for i in range(40):
        ai1 = GeneticAI(loader.get_strategy("CauldronCurse"))
        ai2 = GeneticAI(loader.get_strategy("BigMoney"))
        kingdom_cards = [get_card(name) for name in board.kingdom_cards]
        gs = GameState(players=[], supply={})
        if i % 2 == 0:
            gs.initialize_game([ai1, ai2], kingdom_cards, use_shelters=False)
        else:
            gs.initialize_game([ai2, ai1], kingdom_cards, use_shelters=False)
        _silent_play(gs)
        winner = max(gs.players, key=lambda pp: pp.get_victory_points()).ai
        if winner is ai1:
            cc_wins += 1
        else:
            bm_wins += 1

    assert cc_wins >= 10, (
        f"CauldronCurse only won {cc_wins}/40 vs BigMoney; expected at "
        f"least 10 (~25%) on the seed board (BigMoney won {bm_wins})."
    )


def test_strategy_delivers_curses_to_opponent(loader, board):
    """Across a moderate batch of seeded games the Cauldron trigger
    must fire at least once - direct evidence that the strategy is
    actually executing the curse plan rather than merely playing
    Cauldron as a Silver-with-+Buy.  On this board no other card
    hands out Curses, so any Curse in the opponent's deck comes
    from the Cauldron trigger.

    50 games at ~3-5 curses per 100 games gives an expected count of
    about 1-3 curses per run; we require a single curse so this test
    has plenty of margin against shuffle variance."""

    random.seed(20240429)
    total_curses = 0
    for _ in range(50):
        ai1 = GeneticAI(loader.get_strategy("CauldronCurse"))
        ai2 = GeneticAI(loader.get_strategy("BigMoney"))
        kingdom_cards = [get_card(name) for name in board.kingdom_cards]
        gs = GameState(players=[], supply={})
        gs.initialize_game([ai1, ai2], kingdom_cards, use_shelters=False)
        _silent_play(gs)
        bm_player = next(p for p in gs.players if p.ai is ai2)
        total_curses += sum(1 for c in bm_player.all_cards() if c.name == "Curse")

    assert total_curses >= 1, (
        "CauldronCurse did not deliver a single Curse to BigMoney across "
        "50 seeded games - the third-action Cauldron trigger never fired."
    )
