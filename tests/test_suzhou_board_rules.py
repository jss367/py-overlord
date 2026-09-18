"""Printed-rule regressions for the Suzhou (Groundskeeper) board.

Every card on this board was audited against its printed text while the board
was built. Three of them were wrong; the tests below pin the corrected
behaviour, and the rest guard the interactions the board is built on.
"""

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.strategies.suzhou_groundskeeper import (
    WINNER,
    SuzhouGroundskeeper,
    create_suzhou_groundskeeper_engine,
)
from dominion.strategy.strategy_loader import StrategyLoader
from tests.utils import DummyAI


BOARD = load_board("boards/suzhou.txt")


class GainsAI(DummyAI):
    """Names the pile every gain hook should take, or nothing at all."""

    def __init__(self, wanted=None):
        super().__init__()
        self.wanted = wanted

    def choose_buy(self, state, choices):
        return next((c for c in choices if c is not None and c.name == self.wanted), None)


def state_and_player(ai=None, supply=None):
    player = PlayerState(ai or DummyAI())
    other = PlayerState(DummyAI())
    state = GameState([player, other])
    state.log_callback = lambda *_: None
    state.supply = supply if supply is not None else {
        "Estate": 8, "Duchy": 8, "Province": 8, "Silver": 40,
        "Great Hall": 8, "Nobles": 8, "Ironworks": 10, "Village": 10,
    }
    return state, player


def play(state, player, name):
    """Play ``name`` the way the engine does: into play, then resolve it."""

    card = get_card(name)
    player.in_play.append(card)
    card.on_play(state)
    return card


# -- supply -----------------------------------------------------------------


def test_kingdom_victory_piles_are_eight_in_a_two_player_game():
    """Victory piles are 8 in 2P and 12 above it, not the 10 of an Action."""

    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(SuzhouGroundskeeper()), GeneticAI(SuzhouGroundskeeper())],
        [get_card(name) for name in BOARD.kingdom_cards],
    )
    assert state.supply["Great Hall"] == 8
    assert state.supply["Nobles"] == 8
    assert state.supply["Estate"] == 8
    # Action piles are untouched.
    assert state.supply["Village"] == 10
    assert state.supply["Groundskeeper"] == 10

    three_player = GameState(players=[None, None, None])
    three_player.setup_supply([get_card("Great Hall"), get_card("Village")])
    assert three_player.supply["Great Hall"] == 12
    assert three_player.supply["Village"] == 10


# -- Crossroads -------------------------------------------------------------


def test_crossroads_draws_one_card_per_victory_card_in_hand():
    state, player = state_and_player()
    player.hand = [get_card("Estate"), get_card("Great Hall"), get_card("Copper")]
    player.deck = [get_card("Copper") for _ in range(5)]

    get_card("Crossroads").play_effect(state)

    # Two Victory cards revealed, so two cards drawn; the Crossroads itself is
    # in play and is never one of them.
    assert len(player.hand) == 5


def test_crossroads_gives_three_actions_only_the_first_time_each_turn():
    state, player = state_and_player()
    player.deck = [get_card("Copper") for _ in range(5)]
    player.actions = 1
    player.buys = 1

    get_card("Crossroads").play_effect(state)
    assert (player.actions, player.buys) == (4, 1)

    get_card("Crossroads").play_effect(state)
    assert (player.actions, player.buys) == (4, 1)

    player.crossroads_played = 0
    get_card("Crossroads").play_effect(state)
    assert player.actions == 7


# -- Ironworks --------------------------------------------------------------


def test_crossroads_actions_obey_snowy_village():
    """Snowy Village's "ignore its +Actions" covers Crossroads' +3 too."""

    state, player = state_and_player()
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 1
    player.ignore_action_bonuses = True

    get_card("Crossroads").play_effect(state)

    assert player.actions == 1


def test_ironworks_gain_follows_the_strategy_not_the_pile_order():
    state, player = state_and_player(GainsAI("Great Hall"))
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 0

    get_card("Ironworks").play_effect(state)

    assert [c.name for c in player.discard] == ["Great Hall"]
    assert state.supply["Great Hall"] == 7
    # Great Hall is an Action *and* a Victory card, so it pays both bonuses.
    assert player.actions == 1
    assert [c.name for c in player.hand] == ["Copper"]
    # The unmodified engine gained the most expensive Action instead.
    assert get_card("Ironworks")._default_gain(
        [get_card(n) for n in ("Estate", "Great Hall", "Ironworks")]
    ).name == "Ironworks"


def test_ironworks_gain_is_mandatory_when_the_strategy_declines():
    state, player = state_and_player(GainsAI(None))
    player.deck = [get_card("Copper") for _ in range(3)]

    get_card("Ironworks").play_effect(state)

    assert len(player.all_cards()) == 4


def test_ironworks_uses_the_reduced_cost_after_bridge():
    state, player = state_and_player(GainsAI("Nobles"))
    player.deck = [get_card("Copper") for _ in range(4)]

    get_card("Ironworks").play_effect(state)
    assert not any(c.name == "Nobles" for c in player.all_cards())

    # Two Bridges put a $6 Nobles inside Ironworks' $4 reach.
    player.cost_reduction = 2
    get_card("Ironworks").play_effect(state)
    assert any(c.name == "Nobles" for c in player.all_cards())


# -- Mill -------------------------------------------------------------------


class MillAI(DummyAI):
    """Records what Mill offered and answers with a fixed reply."""

    def __init__(self, reply):
        super().__init__()
        self.reply = reply
        self.seen = None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        self.seen = (reason, count)
        return list(self.reply)


def test_mill_discard_is_optional_and_asks_the_player():
    ai = MillAI([])
    state, player = state_and_player(ai)
    player.hand = [get_card("Gold"), get_card("Province")]

    get_card("Mill").play_effect(state)

    assert ai.seen == ("mill", 2)
    assert player.coins == 0
    assert len(player.hand) == 2, "declining must not discard anything"


def test_mill_pays_two_coins_for_two_discards():
    estates = [get_card("Estate"), get_card("Estate")]
    state, player = state_and_player(MillAI(estates))
    player.hand = estates + [get_card("Gold")]

    get_card("Mill").play_effect(state)

    assert player.coins == 2
    assert [c.name for c in player.hand] == ["Gold"]


def test_mill_discards_two_cards_or_none_at_all():
    """A duplicated or already-played answer must not cost a card for nothing."""

    estate = get_card("Estate")
    gold = get_card("Gold")
    # The AI names the same card twice: one legal discard, so Mill does nothing.
    state, player = state_and_player(MillAI([estate, estate]))
    player.hand = [estate, gold]

    get_card("Mill").play_effect(state)

    assert player.coins == 0
    assert [c.name for c in player.hand] == ["Estate", "Gold"]

    # A card that is no longer in hand is skipped the same way.
    stale = get_card("Copper")
    state, player = state_and_player(MillAI([stale, estate]))
    player.hand = [estate, gold]

    get_card("Mill").play_effect(state)

    assert player.coins == 0
    assert len(player.hand) == 2


def test_the_strategy_only_pays_mill_with_dead_cards():
    strategy = SuzhouGroundskeeper()
    state, player = state_and_player()

    hand = [get_card("Estate"), get_card("Duchy"), get_card("Gold")]
    chosen = strategy.choose_cards_to_discard(state, player, hand, 2, reason="mill")
    assert sorted(c.name for c in chosen) == ["Duchy", "Estate"]

    hand = [get_card("Estate"), get_card("Copper"), get_card("Gold")]
    assert strategy.choose_cards_to_discard(state, player, hand, 2, reason="mill") == []


# -- Groundskeeper ----------------------------------------------------------


def test_groundskeeper_pays_a_token_per_copy_for_every_victory_gain():
    state, player = state_and_player(GainsAI("Great Hall"))
    player.deck = [get_card("Copper") for _ in range(6)]
    player.actions = 2

    play(state, player, "Groundskeeper")
    play(state, player, "Groundskeeper")
    assert player.groundskeeper_bonus == 2
    assert player.vp_tokens == 0

    get_card("Ironworks").play_effect(state)
    assert player.vp_tokens == 2

    state.gain_card(player, get_card("Silver"))
    assert player.vp_tokens == 2, "only Victory gains pay"

    state.gain_card(player, get_card("Estate"))
    assert player.vp_tokens == 4


def test_groundskeeper_bonus_does_not_survive_the_turn():
    state, player = state_and_player()
    player.actions = 1
    play(state, player, "Groundskeeper")
    assert player.groundskeeper_bonus == 1

    state.handle_cleanup_phase()
    assert player.groundskeeper_bonus == 0


# -- the board's strategy family -------------------------------------------


def test_play_order_puts_groundskeeper_and_bridge_before_the_gainers():
    strategy = SuzhouGroundskeeper()
    state, player = state_and_player()
    player.actions = 3
    player.hand = [get_card("Estate")]
    choices = [get_card(n) for n in ("Ironworks", "Bridge", "Groundskeeper")]

    assert strategy.choose_action(state, player, choices).name == "Groundskeeper"
    choices = [c for c in choices if c.name != "Groundskeeper"]
    assert strategy.choose_action(state, player, choices).name == "Bridge"
    choices = [c for c in choices if c.name != "Bridge"]
    assert strategy.choose_action(state, player, choices).name == "Ironworks"


def test_gainers_wait_for_a_groundskeeper_before_taking_green():
    strategy = SuzhouGroundskeeper(green_gate=1, great_hall=99)
    state, player = state_and_player()
    player.turns_taken = 5  # past the fixed opening buys
    choices = [get_card(n) for n in ("Great Hall", "Village", "Ironworks")]

    # Nothing in play yet: the gain goes to an engine piece.
    assert strategy.choose_gain(state, player, choices).name == "Ironworks"

    # With a Groundskeeper out the token is live, so green outranks the
    # engine piece it would otherwise have taken.
    player.groundskeeper_bonus = 1
    assert strategy.choose_gain(state, player, choices).name == "Great Hall"

    # A gate of 0 does not wait at all.
    eager = SuzhouGroundskeeper(green_gate=0, great_hall=99)
    player.groundskeeper_bonus = 0
    assert eager.choose_gain(state, player, choices).name == "Great Hall"


def test_the_opening_buy_is_one_card_taken_within_the_first_two_turns():
    """``turns_taken`` is 1 on the first turn and 2 on the second.

    The opener is a single card the deck wants early, taken on whichever of
    those turns can afford it -- not a copy per turn. Once it owns one, the
    deck plan takes back over, which is what keeps a $5 second turn from
    spending on another $4 opener instead of a Groundskeeper.
    """

    strategy = SuzhouGroundskeeper(opening="Mill")
    state, player = state_and_player()
    state.supply = {"Mill": 8, "Ironworks": 10}
    choices = [get_card("Mill"), get_card("Ironworks")]

    # A first turn too poor for the opener leaves it wanted on the second.
    for turn in (1, 2):
        player.turns_taken = turn
        assert strategy.choose_gain(state, player, choices).name == "Mill"

    # Having gained it, the second turn follows the deck plan instead.
    player.discard.append(get_card("Mill"))
    player.turns_taken = 2
    assert strategy.choose_gain(state, player, choices).name == "Ironworks"

    # And so does every turn after the opening window.
    player.discard.clear()
    player.turns_taken = 3
    assert strategy.choose_gain(state, player, choices).name == "Ironworks"


def test_bridge_discount_is_not_counted_twice_when_sizing_up_a_gain():
    """The Ironworks check uses the current cost, which already has Bridge in it."""

    strategy = SuzhouGroundskeeper()
    state, player = state_and_player()
    state.supply = {"Province": 8, "Nobles": 8}
    player.turns_taken = 5
    player.cost_reduction = 2  # two Bridges played

    # Province is $6 after two Bridges, so Ironworks cannot reach it and
    # playing Ironworks would only buy a forced fallback gain.
    assert strategy._wants_to_gain(state, player) is False

    # Nobles is $4 after the same two Bridges, and a plan that wants Nobles
    # does then want to play Ironworks.
    nobles_buyer = SuzhouGroundskeeper(nobles=2)
    assert nobles_buyer._wants_to_gain(state, player) is True


def test_the_main_buy_of_a_turn_goes_to_the_engine_not_to_cheap_green():
    """A $5 hand that takes a $3 Great Hall has thrown two dollars away."""

    strategy = SuzhouGroundskeeper(green_gate=1, great_hall=99, laboratory=4)
    state, player = state_and_player()
    state.supply["Laboratory"] = 10
    player.turns_taken = 5
    player.groundskeeper_bonus = 2
    # A buy always offers "buy nothing"; a gainer never does.
    choices = [get_card(n) for n in ("Great Hall", "Laboratory")] + [None]

    assert strategy.choose_gain(state, player, choices).name == "Laboratory"

    # The second buy of the same turn is spare, so it goes on the green.
    player.cards_gained_this_buy_phase = 1
    assert strategy.choose_gain(state, player, choices).name == "Great Hall"


def test_a_mandatory_gain_never_returns_nothing():
    strategy = SuzhouGroundskeeper(**{key: 0 for key in ("ironworks", "bridge",
                                                         "village", "crossroads",
                                                         "laboratory", "market",
                                                         "groundskeeper", "great_hall",
                                                         "mill", "silver", "gold")})
    state, player = state_and_player()
    choices = [get_card("Village"), get_card("Great Hall")]

    # A buy may decline; a Workshop or Ironworks gain may not.
    assert strategy.choose_gain(state, player, choices + [None]) is None
    assert strategy.choose_gain(state, player, choices).name == "Great Hall"


def test_the_frozen_winner_is_discoverable_and_unchanged():
    """The published plan is the one the search froze, not a later edit."""

    strategy = StrategyLoader().get_strategy("Suzhou Groundskeeper Engine")
    assert strategy is not None
    assert strategy.params == SuzhouGroundskeeper(**WINNER).params
    assert create_suzhou_groundskeeper_engine().params == strategy.params
    # The claims in the guide are about a three-Groundskeeper plan that gains
    # green from the first turn and spends spare Buys on Estates.
    assert WINNER["groundskeeper"] == 3
    assert WINNER["green_gate"] == 0
    assert WINNER["estate_vp"] is True


def test_the_search_harness_is_reproducible_from_its_seed():
    """Every number in the guide is a seed away from being replayed."""

    from scripts.search_suzhou import WINNER_SPEC, match

    task = (WINNER_SPEC, WINNER_SPEC | {"groundskeeper": 0, "opening": ""}, 4, 4242)
    assert match(task) == match(task)


@pytest.mark.parametrize("seed", [3, 17])
def test_a_full_game_on_the_board_finishes_normally(seed):
    import random

    random.seed(seed)
    state = GameState(players=[], supply={})
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(SuzhouGroundskeeper()), GeneticAI(SuzhouGroundskeeper(groundskeeper=0))],
        [get_card(name) for name in BOARD.kingdom_cards],
    )
    while not state.is_game_over() and state.turn_number < 120:
        state.play_turn()

    assert state._normal_game_end_reached()
    assert state.players[0].vp_tokens > 0
