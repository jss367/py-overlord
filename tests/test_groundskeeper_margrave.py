"""Setup, hook forwarding, and policy checks for the ten-unused-card board."""

from collections import Counter

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.groundskeeper_margrave import GroundskeeperMargrave


BOARD_PATH = "boards/groundskeeper_margrave.txt"

EXPECTED_KINGDOM = [
    "Cellar",
    "Oasis",
    "Fishing Village",
    "Moneylender",
    "Monument",
    "Junk Dealer",
    "Library",
    "Margrave",
    "Groundskeeper",
    "Border Village",
]


def board_state(strategy=None, players=2):
    board = load_board(BOARD_PATH)
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(strategy or GroundskeeperMargrave()) for _ in range(players)],
        [get_card(name) for name in board.kingdom_cards],
    )
    return state


def test_board_lists_the_ten_intended_piles_and_no_landscapes():
    board = load_board(BOARD_PATH)
    assert board.kingdom_cards == EXPECTED_KINGDOM
    assert not board.events
    assert not board.projects
    assert not board.ways
    assert not board.landmarks
    assert not board.allies
    assert board.prophecy is None
    assert board.card_cost_reduction == 0


def test_setup_is_a_plain_two_player_kingdom():
    state = board_state()
    for absent in ("Colony", "Platinum", "Potion"):
        assert absent not in state.supply
    for player in state.players:
        assert Counter(c.name for c in player.all_cards()) == {"Copper": 7, "Estate": 3}


def test_groundskeeper_scores_a_token_for_each_victory_card_gained():
    state = board_state()
    player = state.current_player
    player.vp_tokens = 0
    get_card("Groundskeeper").on_play(state)
    get_card("Groundskeeper").on_play(state)
    assert player.groundskeeper_bonus == 2

    state.gain_card(player, get_card("Estate"))
    assert player.vp_tokens == 2
    # Non-victory gains score nothing.
    state.gain_card(player, get_card("Silver"))
    assert player.vp_tokens == 2


def test_genetic_ai_forwards_moneylender_and_junk_dealer_hooks():
    """These hooks had no strategy override before this board was added."""
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    ai = player.ai

    # Seven starting Coppers is above the strategy's floor of three.
    assert ai.should_trash_copper_for_moneylender(state, player) is True

    player.deck = [get_card("Copper") for _ in range(3)]
    player.discard = []
    player.hand = []
    assert ai.should_trash_copper_for_moneylender(state, player) is False

    # With only three Coppers left, Junk Dealer takes the Estate instead.
    choices = [get_card("Copper"), get_card("Estate")]
    assert ai.choose_card_to_trash_with_junk_dealer(state, player, choices).name == (
        "Estate"
    )


def test_junk_dealer_never_eats_an_engine_piece_when_a_spare_exists():
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    player.deck = []
    player.discard = []
    player.hand = []
    choices = [get_card("Margrave"), get_card("Silver")]
    assert strategy.choose_card_to_trash_with_junk_dealer(
        state, player, choices
    ).name == "Silver"


def test_library_keeps_a_village_but_skips_a_terminal_with_no_actions_left():
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    player.actions = 0
    assert strategy.should_keep_library_action(state, player, get_card("Margrave")) is (
        False
    )
    assert strategy.should_keep_library_action(
        state, player, get_card("Fishing Village")
    ) is True
