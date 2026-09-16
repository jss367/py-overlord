"""Setup, hook forwarding, and policy checks for the ten-unused-card board."""

from collections import Counter

import pytest

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


def test_library_sets_aside_every_action_once_no_actions_remain():
    """Library puts kept cards in hand without playing them, and this board

    grants no Villagers, so with no Actions left even a village is dead weight
    that costs a replacement draw. Exercised through ``GeneticAI`` so a broken
    forwarding method cannot pass.
    """
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    ai = player.ai

    player.actions = 1
    assert ai.should_keep_library_action(state, player, get_card("Margrave")) is True
    assert (
        ai.should_keep_library_action(state, player, get_card("Fishing Village"))
        is True
    )

    player.actions = 0
    assert ai.should_keep_library_action(state, player, get_card("Margrave")) is False
    assert (
        ai.should_keep_library_action(state, player, get_card("Fishing Village"))
        is False
    )


def test_library_draws_a_full_hand_past_stranded_actions():
    """The set-aside cards are discarded, so Library still refills to seven."""
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    player.actions = 0
    player.hand = []
    player.discard = []
    # ``deck`` is drawn from the end, so the villages come off the top first.
    player.deck = [get_card("Copper") for _ in range(7)]
    player.deck += [get_card("Fishing Village") for _ in range(4)]

    get_card("Library").play_effect(state)

    assert len(player.hand) == 7
    assert all(card.name == "Copper" for card in player.hand)
    assert Counter(c.name for c in player.discard)["Fishing Village"] == 4


def test_junk_dealer_spends_a_last_copper_before_an_engine_piece():
    """The three-Copper floor ranks junk; it is not a hard reserve.

    Junk Dealer's trash is mandatory, so a hand with no junk left gives up its
    cheapest spare. Protecting the last Coppers there would feed Junk Dealer a
    Silver instead, which measured worse.
    """
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    player.deck = [get_card("Copper") for _ in range(3)]
    player.discard = []
    player.hand = []

    choices = [get_card("Margrave"), get_card("Copper"), get_card("Silver")]
    assert strategy.choose_card_to_trash_with_junk_dealer(
        state, player, choices
    ).name == "Copper"


def test_cellar_discards_only_junk_even_when_the_hand_is_short_of_it():
    """Cellar's discard is optional, so a short list is the right answer."""
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    hand = [get_card("Copper"), get_card("Gold"), get_card("Margrave")]

    picks = strategy.choose_cards_to_discard(
        state, player, hand, len(hand), reason="cellar"
    )
    assert [c.name for c in picks] == ["Copper"]


@pytest.mark.parametrize("reason", [None, "the_suns_gift", "vault", "hamlet_action"])
def test_optional_discards_never_give_up_a_good_card(reason):
    """An optional discard must stay short rather than shed Provinces and Golds.

    The Sun's Gift reveals four cards and calls this hook with every one of
    them and no ``reason`` (``dominion/boons.py``), because each card may be
    discarded *or* put back. Filling the requested count there would throw away
    the whole reveal. The hook's contract is "up to ``count``", so returning
    only the junk is both legal and correct.
    """
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    player = state.current_player
    revealed = [
        get_card("Province"),
        get_card("Gold"),
        get_card("Margrave"),
        get_card("Copper"),
    ]

    picks = strategy.choose_cards_to_discard(
        state, player, revealed, len(revealed), reason=reason
    )
    assert [c.name for c in picks] == ["Copper"]


def test_mandatory_discards_are_topped_up_by_the_engine_not_the_strategy():
    """A short answer to a mandatory discard is safe: the caller fills it.

    Militia stands in for the whole family of hand-size attacks. The strategy
    offers only its junk; the card's own fallback discards down to three. This
    is why the hook does not need to guess which effects are mandatory.
    """
    strategy = GroundskeeperMargrave()
    state = board_state(strategy)
    target = state.players[1]
    hand = [
        get_card("Copper"),
        get_card("Gold"),
        get_card("Margrave"),
        get_card("Library"),
        get_card("Silver"),
    ]

    # The strategy offers one card for a request of two.
    picks = strategy.choose_cards_to_discard(state, target, hand, 2, reason="militia")
    assert [c.name for c in picks] == ["Copper"]

    # Militia still gets the target down to three.
    target.hand = list(hand)
    get_card("Militia").play_effect(state)
    assert len(target.hand) == 3
    assert "Copper" not in [c.name for c in target.hand]
